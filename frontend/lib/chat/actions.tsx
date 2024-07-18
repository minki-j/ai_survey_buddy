import 'server-only'

import {
  createAI,
  createStreamableUI,
  getMutableAIState,
  getAIState,
  streamUI,
  createStreamableValue
} from 'ai/rsc'

import { z } from 'zod'
import { EventsSkeleton } from '@/components/stocks/events-skeleton'
import { Events } from '@/components/stocks/events'

import {
  formatNumber,
  runAsyncFnWithoutBlocking,
  sleep,
  nanoid
} from '@/lib/utils'
import { saveReview } from '@/app/actions'
import {
  SpinnerMessage,
  UserMessage,
  BotMessage
} from '@/components/stocks/message'
import {PickVendor} from '@/components/stocks/pick-vendor'
import { Review, Message } from '@/lib/types'
import { auth } from '@/auth'


let api_url =process.env['API_URL']

async function submitUserMessage(message: string, reviewId: string) {
  'use server'

  const aiState = getMutableAIState<typeof AI>()
  
  aiState.update({
    ...aiState.get(),
    messages: [
      ...aiState.get().messages,
      {
        id: nanoid(),
        role: 'user',
        content: message,
      }
    ]
  })

  const session = await auth()

  if (!session || !session.user) return
  const formData = new FormData()
  formData.append('user_id', session.user.id)
  formData.append('review_id', reviewId)
  formData.append('user_msg', message)
  
  const url = api_url + 'chat/invoke'
  
  // ! I need to use tool to use StreamUI function from Vercel AI SDK.. But I couldn't since I'm not calling LLM call here. I'm using FastAPI endpoints that calls LLMs.
  const res = await fetch(url, {
    method: 'POST',
    body: formData
  })
  // console.log('res: ', res);
  

  if (!res.ok) {
    throw new Error(`HTTP error! status: ${res.status}`)
  }

  const data = await res.json()
  // console.log("======= data =======\n", data);

  type ComponentMapType = {
    [key: string]: JSX.Element
  }

  const componentMap: ComponentMapType = {
    message: <BotMessage content={data.message} />,
    pick_vendor: <PickVendor />
  }

  
  const display = componentMap[data.uiType]

  return {
    id: nanoid(),
    role: 'ai',
    display: display
  }
}

//AI State refers to the state of the application in a serialisable format that will be used on the server and can be shared with the language model.
export type AIState = {
  reviewId: string
  messages: Message[]
}

export type UIState = {
  id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  display: React.ReactNode
}[]

export const AI = createAI<AIState, UIState>({
  actions: {
    submitUserMessage
  },
  initialUIState: [],
  initialAIState: { reviewId: nanoid(), messages: [] },
  onGetUIState: async () => {
    'use server'
    console.log('onGetUIState');
    

    const session = await auth()

    if (session && session.user) {
      const aiState = getAIState()

      if (aiState) {
        const uiState = getUIStateFromAIState(aiState)
        // console.log('uiState: ', uiState)

        return uiState
      }
    } else {
      return
    }
  },
  // runs whenever the AI state is updated
  onSetAIState: async ({ state }) => {
    'use server'
    // console.log('onSetAIState state: ', state);
  }
})

export const getUIStateFromAIState = (aiState: Review) => {
  return aiState.messages
    .filter(message => message.role !== 'system')
    .map((message, index) => ({
      id: `${aiState.chatId}-${index}`,
      role: message.role,
      display:
        message.role === 'tool' ? (
          message.content.map(tool => {
            console.log('tool in messages: ', tool)
            // TODO: Implement ToolMessage component
            return <BotMessage key={nanoid()} content={message.content} />
          })
        ) : message.role === 'user' ? (
          <UserMessage>{message.content as string}</UserMessage>
        ) : message.role === 'assistant' &&
          typeof message.content === 'string' ? (
          <BotMessage content={message.content} />
        ) : null
    }))
}
