export interface Board {
  id: number
  name: string
  description: string
}

export interface Reply {
  id: number
  body: string
  comment_id: number
  created_at: string
  votes: number
  user_id: number | null
}

export interface Comment {
  id: number
  body: string
  post_id: number
  created_at: string
  votes: number
  user_id: number | null
  replies: Reply[]
}

export interface Post {
  id: number
  title: string
  body: string
  board_id: number
  created_at: string
  votes: number
  user_id: number | null
  comments: Comment[]
}