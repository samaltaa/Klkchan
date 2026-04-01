'use client'

import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getBoards, getPostsByBoard, createComment, createReply } from '@/api'
import { Board, Post, Comment } from '@/types'

export default function ThreadPage() {
  const router = useRouter()
  const boardName = router.query.board as string
  const postId = Number(router.query.postId)

  const [board, setBoard] = useState<Board | null>(null)
  const [post, setPost] = useState<Post | null>(null)
  const [loading, setLoading] = useState(true)
  const [commentBody, setCommentBody] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [replyingTo, setReplyingTo] = useState<number | null>(null)
  const [replyBody, setReplyBody] = useState('')

  async function loadPost(boardObj: Board) {
    const posts = await getPostsByBoard(boardObj.id)
    const found = posts.find((p) => p.id === postId)
    setPost(found || null)
  }

  useEffect(() => {
    if (!boardName || !postId) return
    async function load() {
      try {
        const boards = await getBoards()
        const found = boards.find((b) => b.name.toLowerCase() === boardName.toLowerCase())
        if (!found) { setLoading(false); return }
        setBoard(found)
        await loadPost(found)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [boardName, postId])

  async function handleComment(e: React.FormEvent) {
    e.preventDefault()
    if (!commentBody.trim() || !post || !board) return
    setSubmitting(true)
    try {
      await createComment({ body: commentBody, post_id: post.id })
      setCommentBody('')
      await loadPost(board)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleReply(e: React.FormEvent, commentId: number) {
    e.preventDefault()
    if (!replyBody.trim() || !board) return
    setSubmitting(true)
    try {
      await createReply({ body: replyBody, comment_id: commentId })
      setReplyBody('')
      setReplyingTo(null)
      await loadPost(board)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <div className="min-h-screen bg-[#eef2ff] p-4 text-xs text-gray-500">Loading...</div>
  if (!board || !post) return <div className="min-h-screen bg-[#eef2ff] p-4 text-xs text-red-500">Thread not found.</div>

  return (
    <main className="min-h-screen bg-[#eef2ff]">
      {/* Header */}
      <header className="bg-[#af0a0f] text-white text-center py-3 border-b-4 border-[#800000]">
        <Link href={`/${board.name}`} className="text-red-200 text-xs hover:underline block mb-0.5">
          ← /{board.name}/
        </Link>
        <h1 className="text-xl font-bold">/{board.name}/ — {board.description}</h1>
      </header>

      <div className="max-w-4xl mx-auto px-3 mt-4 pb-10 space-y-2">

        {/* OP post */}
        <div className="bg-[#f0e0d6] border border-[#d9bfb7] p-2 inline-block max-w-full">
          <div className="text-xs text-gray-600 mb-1 flex gap-3 flex-wrap">
            <span className="text-[#117743] font-bold">Anonymous</span>
            <span>{new Date(post.created_at).toLocaleString()}</span>
            <span className="text-[#34345c]">No.{post.id}</span>
            {post.title && <span className="text-[#0f0c5d] font-bold">{post.title}</span>}
          </div>
          <p className="text-xs whitespace-pre-wrap break-words max-w-prose">{post.body}</p>
        </div>

        <hr className="border-[#b7c5d9]" />

        {/* Reply to thread form */}
        <form onSubmit={handleComment} className="bg-[#d6daf0] border border-[#b7c5d9] p-3 text-xs space-y-2 inline-block">
          <div className="font-bold text-[#af0a0f] mb-1">Reply to Thread</div>
          <div className="flex gap-2 items-start">
            <label className="w-16 text-right text-gray-600 mt-0.5">Comment</label>
            <textarea
              className="border border-[#b7c5d9] bg-white px-2 py-0.5 text-xs min-h-[60px] w-72"
              value={commentBody}
              onChange={e => setCommentBody(e.target.value)}
              required
            />
          </div>
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={submitting}
              className="bg-[#af0a0f] text-white px-4 py-1 text-xs hover:bg-[#800000] disabled:opacity-50"
            >
              {submitting ? 'Posting...' : 'Post'}
            </button>
          </div>
        </form>

        <hr className="border-[#b7c5d9]" />

        {/* Comments */}
        {post.comments.length === 0 && (
          <p className="text-xs text-gray-500">No replies yet.</p>
        )}

        {post.comments.map((comment: Comment) => (
          <div key={comment.id} className="ml-4">
            {/* Comment */}
            <div className="bg-[#d6daf0] border border-[#b7c5d9] p-2 inline-block max-w-full">
              <div className="text-xs text-gray-600 mb-1 flex gap-3 flex-wrap">
                <span className="text-[#117743] font-bold">Anonymous</span>
                <span>{new Date(comment.created_at).toLocaleString()}</span>
                <span className="text-[#34345c]">No.{comment.id}</span>
                <button
                  className="text-[#34345c] hover:text-[#af0a0f] underline"
                  onClick={() => setReplyingTo(replyingTo === comment.id ? null : comment.id)}
                >
                  Reply
                </button>
              </div>
              <p className="text-xs whitespace-pre-wrap break-words max-w-prose">{comment.body}</p>
            </div>

            {/* Inline reply form */}
            {replyingTo === comment.id && (
              <form
                onSubmit={e => handleReply(e, comment.id)}
                className="mt-1 ml-4 bg-[#eef2ff] border border-[#b7c5d9] p-2 text-xs space-y-1 inline-block"
              >
                <textarea
                  className="border border-[#b7c5d9] bg-white px-2 py-0.5 text-xs min-h-[50px] w-64"
                  value={replyBody}
                  onChange={e => setReplyBody(e.target.value)}
                  placeholder="Write a reply..."
                  required
                  autoFocus
                />
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={submitting}
                    className="bg-[#af0a0f] text-white px-3 py-0.5 text-xs hover:bg-[#800000] disabled:opacity-50"
                  >
                    Post
                  </button>
                  <button
                    type="button"
                    onClick={() => setReplyingTo(null)}
                    className="text-xs text-gray-500 hover:text-gray-700"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}

            {/* Replies */}
            {comment.replies.length > 0 && (
              <div className="ml-8 mt-1 space-y-1">
                {comment.replies.map((reply) => (
                  <div key={reply.id} className="bg-[#eef2ff] border border-[#b7c5d9] p-2 inline-block max-w-full">
                    <div className="text-xs text-gray-600 mb-1 flex gap-3">
                      <span className="text-[#117743] font-bold">Anonymous</span>
                      <span>{new Date(reply.created_at).toLocaleString()}</span>
                      <span className="text-[#34345c]">No.{reply.id}</span>
                      <span className="text-gray-400">&gt;&gt;{comment.id}</span>
                    </div>
                    <p className="text-xs whitespace-pre-wrap break-words max-w-prose">{reply.body}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </main>
  )
}