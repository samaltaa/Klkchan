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
  const [commentImage, setCommentImage] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [replyingTo, setReplyingTo] = useState<number | null>(null)
  const [replyBody, setReplyBody] = useState('')
  const [replyImage, setReplyImage] = useState<File | null>(null)

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
      await createComment({ body: commentBody, post_id: post.id, image: commentImage })
      setCommentBody('')
      setCommentImage(null)
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
      await createReply({ body: replyBody, comment_id: commentId, image: replyImage })
      setReplyBody('')
      setReplyImage(null)
      setReplyingTo(null)
      await loadPost(board)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <div className="min-h-screen bg-[#eef2ff] flex items-center justify-center text-sm text-gray-500">Loading...</div>
  if (!board || !post) return <div className="min-h-screen bg-[#eef2ff] flex items-center justify-center text-sm text-red-500">Thread not found.</div>

  return (
    <main className="min-h-screen bg-[#eef2ff]">
      <header className="bg-[#af0a0f] text-white text-center py-3 border-b-4 border-[#800000]">
        <Link href={`/${board.name}`} className="text-red-200 text-sm hover:underline block mb-0.5">
          ← /{board.name}/
        </Link>
        <h1 className="text-2xl font-bold">/{board.name}/ — {board.description}</h1>
      </header>

      <div className="max-w-3xl mx-auto px-4 mt-6 pb-12 space-y-4">

        <div className="bg-[#f0e0d6] border border-[#d9bfb7] p-3 w-full">
          <div className="text-sm text-gray-600 mb-2 flex gap-4 flex-wrap items-center">
            <span className="text-[#117743] font-bold">Anonymous</span>
            <span>{new Date(post.created_at).toLocaleString()}</span>
            <span className="text-[#34345c]">No.{post.id}</span>
            {post.title && <span className="text-[#0f0c5d] font-bold">{post.title}</span>}
          </div>
          {post.image_url && (
            <img
              src={post.image_url}
              alt="post image"
              className="max-h-64 mb-2 border border-[#d9bfb7]"
            />
          )}
          <p className="text-sm whitespace-pre-wrap break-words">{post.body}</p>
        </div>

        <hr className="border-[#b7c5d9]" />

        <form onSubmit={handleComment} className="bg-[#d6daf0] border border-[#b7c5d9] p-4 text-sm space-y-3 w-full">
          <div className="font-bold text-[#af0a0f]">Reply to Thread</div>
          <div className="flex gap-3 items-start">
            <label className="w-20 text-right text-gray-600 mt-1">Comment</label>
            <textarea
              className="flex-1 border border-[#b7c5d9] bg-white px-2 py-1 text-sm min-h-[80px]"
              value={commentBody}
              onChange={e => setCommentBody(e.target.value)}
              required
            />
          </div>
          <div className="flex gap-3 items-center">
            <label className="w-20 text-right text-gray-600">Image</label>
            <input
              type="file"
              accept="image/jpeg,image/jpg,image/png,image/gif,image/webp"
              className="text-sm text-gray-600"
              onChange={e => setCommentImage(e.target.files?.[0] ?? null)}
            />
          </div>
          {commentImage && (
            <div className="flex gap-3 items-center">
              <div className="w-20" />
              <img
                src={URL.createObjectURL(commentImage)}
                alt="preview"
                className="max-h-32 border border-[#b7c5d9]"
              />
            </div>
          )}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={submitting}
              className="bg-[#af0a0f] text-white px-5 py-1.5 text-sm hover:bg-[#800000] disabled:opacity-50"
            >
              {submitting ? 'Posting...' : 'Post'}
            </button>
          </div>
        </form>

        <hr className="border-[#b7c5d9]" />

        {post.comments.length === 0 && (
          <p className="text-sm text-gray-500">No replies yet.</p>
        )}

        {post.comments.map((comment: Comment) => (
          <div key={comment.id} className="ml-4 space-y-2">
            <div className="bg-[#d6daf0] border border-[#b7c5d9] p-3 w-full">
              <div className="text-sm text-gray-600 mb-2 flex gap-4 flex-wrap items-center">
                <span className="text-[#117743] font-bold">Anonymous</span>
                <span>{new Date(comment.created_at).toLocaleString()}</span>
                <span className="text-[#34345c]">No.{comment.id}</span>
                <button
                  className="text-[#34345c] hover:text-[#af0a0f] underline font-bold ml-auto"
                  onClick={() => setReplyingTo(replyingTo === comment.id ? null : comment.id)}
                >
                  {replyingTo === comment.id ? 'Cancel Reply' : 'Reply to Comment'}
                </button>
              </div>
              {comment.image_url && (
                <img
                  src={comment.image_url}
                  alt="comment image"
                  className="max-h-48 mb-2 border border-[#b7c5d9]"
                />
              )}
              <p className="text-sm whitespace-pre-wrap break-words">{comment.body}</p>
            </div>

            {replyingTo === comment.id && (
              <form
                onSubmit={e => handleReply(e, comment.id)}
                className="ml-8 bg-[#eef2ff] border border-[#b7c5d9] p-3 text-sm space-y-2 w-full"
              >
                <div className="font-bold text-[#af0a0f]">Reply to Comment No.{comment.id}</div>
                <textarea
                  className="w-full border border-[#b7c5d9] bg-white px-2 py-1 text-sm min-h-[70px]"
                  value={replyBody}
                  onChange={e => setReplyBody(e.target.value)}
                  placeholder="Write a reply..."
                  required
                  autoFocus
                />
                <div className="flex gap-3 items-center">
                  <label className="text-gray-600">Image</label>
                  <input
                    type="file"
                    accept="image/jpeg,image/jpg,image/png,image/gif,image/webp"
                    className="text-sm text-gray-600"
                    onChange={e => setReplyImage(e.target.files?.[0] ?? null)}
                  />
                </div>
                {replyImage && (
                  <img
                    src={URL.createObjectURL(replyImage)}
                    alt="preview"
                    className="max-h-32 border border-[#b7c5d9]"
                  />
                )}
                <div className="flex gap-2 justify-end">
                  <button
                    type="button"
                    onClick={() => { setReplyingTo(null); setReplyImage(null) }}
                    className="text-sm text-gray-500 hover:text-gray-700 px-3 py-1 border border-gray-300"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="bg-[#af0a0f] text-white px-4 py-1 text-sm hover:bg-[#800000] disabled:opacity-50"
                  >
                    {submitting ? 'Posting...' : 'Post Reply'}
                  </button>
                </div>
              </form>
            )}

            {comment.replies.length > 0 && (
              <div className="ml-8 space-y-2">
                {comment.replies.map((reply) => (
                  <div key={reply.id} className="bg-[#eef2ff] border border-[#b7c5d9] p-3 w-full">
                    <div className="text-sm text-gray-600 mb-1 flex gap-4 flex-wrap">
                      <span className="text-[#117743] font-bold">Anonymous</span>
                      <span>{new Date(reply.created_at).toLocaleString()}</span>
                      <span className="text-[#34345c]">No.{reply.id}</span>
                      <span className="text-gray-400">&gt;&gt;{comment.id}</span>
                    </div>
                    {reply.image_url && (
                      <img
                        src={reply.image_url}
                        alt="reply image"
                        className="max-h-48 mb-2 border border-[#b7c5d9]"
                      />
                    )}
                    <p className="text-sm whitespace-pre-wrap break-words">{reply.body}</p>
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