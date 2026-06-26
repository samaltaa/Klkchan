import {Board, Post} from '@/types'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

export async function getBoards(): Promise<Board[]> {

    const response = await fetch(`${BASE_URL}/getboards`, {cache: 'no-store'})
    if (!response.ok) throw new Error('failed to fetch boards')
    
    return response.json()
}

export async function getBoardByName(name: string): Promise<Board | undefined> {

    const boards = await getBoards()
    return boards.find((board) => board.name.toLocaleLowerCase() === name.toLocaleLowerCase())

}

export  async function getPostsByBoard(boardId: number): Promise<Post[]> {

    const response = await fetch(`${BASE_URL}/boards/${boardId}/posts`, {cache: 'no-store'})
    if (!response.ok) throw new Error('Failed to fetch posts')
    return response.json()

}

export async function getPost(postId: number): Promise<Post> {

    const posts = await fetch(`${BASE_URL}/getposts`, {cache: 'no-store'})
    .then(response => response.json()) as Post[]

    const post = posts.find(post => post.id === postId)
    if (!post) throw new Error('Post not found')
    return post

}

export async function createPost(payload: {
    title: string
    body: string
    board_id: number
    user_id: null
    image?: File | null
}): Promise<Post>{

    const form = new FormData()
    form.append('body', payload.body)
    form.append('board_id', String(payload.board_id))
    if (payload.title) form.append('title', payload.title)
    if (payload.image) form.append('image', payload.image)

    const response = await fetch(`${BASE_URL}/posts`, {
        method: 'POST',
        body: form
    })

    if (!response.ok) throw new Error('Failed to create post')
    return response.json()

}

export async function createComment(payload: {
    body: string
    post_id: number
    image?: File | null
}): Promise<Comment> {

    const form = new FormData()
    form.append('body', payload.body)
    form.append('post_id', String(payload.post_id))
    if (payload.image) form.append('image', payload.image)

    const response = await fetch(`${BASE_URL}/comments`, {
        method: 'POST',
        body: form,
    })

    if (!response.ok) throw new Error('Failed to create comment')
    return response.json()
}

export async function createReply(payload: {
    body: string
    comment_id: number
    image?: File | null
}): Promise<Comment> {
    
    const form = new FormData()
    form.append('body', payload.body)
    form.append('comment_id', String(payload.comment_id))
    if (payload.image) form.append('image', payload.image)

    const response = await fetch(`${BASE_URL}/replies`, {
        method: 'POST',
        body: form,
    })
    if (!response.ok) throw new Error('Failed to create reply')
    return response.json()
}