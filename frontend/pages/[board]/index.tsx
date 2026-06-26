import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getBoards, getPostsByBoard, createPost } from '@/api'
import { Board, Post } from '@/types'

export default function BoardPage() {
  const router = useRouter()
  const boardName = router.query.board as string

  const [board, setBoard] = useState<Board | null>(null)
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ title: '', body: '' })
  const [image, setImage] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [expandedReplies, setExpandedReplies] = useState<Set<number>>(new Set())

  async function loadPosts(boardObj: Board) {
    const fresh = await getPostsByBoard(boardObj.id)
    setPosts([...fresh].sort((a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    ))
  }

  useEffect(() => {
    if (!boardName) return
    async function load() {
      try {
        const boards = await getBoards()
        const found = boards.find((b) => b.name.toLowerCase() === boardName.toLowerCase())
        if (!found) { setLoading(false); return }
        setBoard(found)
        await loadPosts(found)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [boardName])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!board || !form.body.trim()) return
    setSubmitting(true)
    try {
      await createPost({ 
        title: form.title, 
        body: form.body, 
        board_id: board.id, 
        user_id: null,
        image})

      setForm({ title: '', body: '' })
      setImage(null)
      setShowForm(false)
      await loadPosts(board)
    } finally {
      setSubmitting(false)
    }
  }

  function toggleReplies(commentId: number) {
    setExpandedReplies(prev => {
      const next = new Set(prev)
      next.has(commentId) ? next.delete(commentId) : next.add(commentId)
      return next
    })
  }

  if (loading) return <div className="min-h-screen bg-[#eef2ff] flex items-center justify-center text-sm text-gray-500">Loading...</div>
  if (!board) return <div className="min-h-screen bg-[#eef2ff] flex items-center justify-center text-sm text-red-500">Board not found.</div>

  return (
    <main className="min-h-screen bg-[#eef2ff]">
      <header className="bg-[#af0a0f] text-white text-center py-3 border-b-4 border-[#800000]">
        <Link href="/" className="text-red-200 text-sm hover:underline block mb-0.5">← home</Link>
        <h1 className="text-2xl font-bold">/{board.name}/ — {board.description}</h1>
      </header>

      <div className="max-w-3xl mx-auto px-4 mt-6">
        <button
          onClick={() => setShowForm(!showForm)}
          className="text-sm bg-[#d6daf0] border border-[#b7c5d9] px-4 py-1.5 hover:bg-[#c8cde8] text-[#34345c] font-bold"
        >
          {showForm ? 'Cancel' : '[ Start a New Thread ]'}
        </button>

        {showForm && (
          <form onSubmit={handleSubmit} className="mt-3 bg-[#d6daf0] border border-[#b7c5d9] p-4 text-sm space-y-3">
            <div className="flex gap-3 items-center">
              <label className="w-20 text-right text-gray-600">Subject</label>
              <input
                className="flex-1 border border-[#b7c5d9] bg-white px-2 py-1 text-sm"
                value={form.title}
                onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                placeholder="Optional"
              />
            </div>

            <div className="flex gap-3 items-start">
              <label className="w-20 text-right text-gray-600 mt-1">Comment</label>
              <textarea
                className="flex-1 border border-[#b7c5d9] bg-white px-2 py-1 text-sm min-h-[100px]"
                value={form.body}
                onChange={e => setForm(f => ({ ...f, body: e.target.value }))}
                required
              />
            </div>

            <div className="flex gap-3 items-center">
              <label className="w-20 text-right text-gray-600">Image</label>
              <input
                type="file"
                accept="image/jpeg,image/jpg,image/png,image/gif,image/webp"
                className="text-sm text-gray-600"
                onChange={e => setImage(e.target.files?.[0] ?? null)}
              />
            </div>

            {image && (
              <div className="flex gap-3 items-center">
                <div className="w-20" />
                  <img
                    src={URL.createObjectURL(image)}
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
        )}
      </div>

      <hr className="border-[#b7c5d9] my-4 max-w-3xl mx-auto" />

      <div className="max-w-3xl mx-auto px-4 space-y-8 pb-12">
        {posts.length === 0 && (
          <p className="text-sm text-gray-500">No posts yet. Be the first to post.</p>
        )}

        {posts.map((post) => (
          <div key={post.id} className="space-y-2">
            <div className="bg-[#f0e0d6] border border-[#d9bfb7] p-3 w-full">
              <div className="text-sm text-gray-600 mb-2 flex gap-4 flex-wrap items-center">
                <span className="text-[#117743] font-bold">Anonymous</span>
                <span>{new Date(post.created_at).toLocaleString()}</span>
                <span className="text-[#34345c]">No.{post.id}</span>
                {post.title && <span className="text-[#0f0c5d] font-bold">{post.title}</span>}
                <Link
                  href={`/${board.name}/thread/${post.id}`}
                  className="ml-auto text-[#34345c] hover:text-[#af0a0f] underline font-bold text-sm"
                >
                  Reply to Post
                </Link>
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

            {post.comments.length > 0 && (
              <div className="ml-8 space-y-2">
                {post.comments.slice(0, 2).map((comment) => (
                  <div key={comment.id} className="space-y-1">
                    <div className="bg-[#d6daf0] border border-[#b7c5d9] p-3 w-full">
                      <div className="text-sm text-gray-600 mb-2 flex gap-4 flex-wrap items-center">
                        <span className="text-[#117743] font-bold">Anonymous</span>
                        <span>{new Date(comment.created_at).toLocaleString()}</span>
                        <span className="text-[#34345c]">No.{comment.id}</span>
                        {comment.replies.length > 0 && (
                          <button
                            onClick={() => toggleReplies(comment.id)}
                            className="text-[#34345c] hover:text-[#af0a0f] underline font-bold"
                          >
                            {comment.replies.length} {comment.replies.length === 1 ? 'reply' : 'replies'}
                            {expandedReplies.has(comment.id) ? ' ▲' : ' ▼'}
                          </button>
                        )}
                        <Link
                          href={`/${board.name}/thread/${post.id}`}
                          className="ml-auto text-[#34345c] hover:text-[#af0a0f] underline font-bold text-sm"
                        >
                          Reply to Comment
                        </Link>
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

                    {expandedReplies.has(comment.id) && comment.replies.length > 0 && (
                      <div className="ml-8 space-y-1">
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

                <div className="text-sm mt-1">
                  {post.comments.length > 2 && (
                    <span className="text-gray-500 mr-2">
                      {post.comments.length - 2} post{post.comments.length - 2 !== 1 ? 's' : ''} omitted.
                    </span>
                  )}
                  <Link
                    href={`/${board.name}/thread/${post.id}`}
                    className="text-[#34345c] hover:text-[#af0a0f] underline font-bold"
                  >
                    {post.comments.length > 2 ? 'See All Replies' : 'View Thread'}
                  </Link>
                </div>
              </div>
            )}

            {post.comments.length === 0 && (
              <div className="ml-8 text-sm">
                <Link
                  href={`/${board.name}/thread/${post.id}`}
                  className="text-[#34345c] hover:text-[#af0a0f] underline font-bold"
                >
                  [ View Thread ]
                </Link>
              </div>
            )}
          </div>
        ))}
      </div>
    </main>
  )
}