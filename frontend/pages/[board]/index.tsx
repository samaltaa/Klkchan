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
  const [submitting, setSubmitting] = useState(false)

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
      await createPost({ title: form.title, body: form.body, board_id: board.id, user_id: null })
      setForm({ title: '', body: '' })
      setShowForm(false)
      await loadPosts(board)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <div className="min-h-screen bg-[#eef2ff] p-4 text-xs text-gray-500">Loading...</div>
  if (!board) return <div className="min-h-screen bg-[#eef2ff] p-4 text-xs text-red-500">Board not found.</div>

  return (
    <main className="min-h-screen bg-[#eef2ff]">
      {/* Header */}
      <header className="bg-[#af0a0f] text-white text-center py-3 border-b-4 border-[#800000]">
        <Link href="/" className="text-red-200 text-xs hover:underline block mb-0.5">← home</Link>
        <h1 className="text-xl font-bold">/{board.name}/ — {board.description}</h1>
      </header>

      {/* New Thread button */}
      <div className="max-w-4xl mx-auto px-3 mt-4">
        <button
          onClick={() => setShowForm(!showForm)}
          className="text-xs bg-[#d6daf0] border border-[#b7c5d9] px-3 py-1 hover:bg-[#c8cde8] text-[#34345c] font-bold"
        >
          {showForm ? 'Cancel' : '[ Start a New Thread ]'}
        </button>

        {showForm && (
          <form onSubmit={handleSubmit} className="mt-2 bg-[#d6daf0] border border-[#b7c5d9] p-3 text-xs space-y-2">
            <div className="flex gap-2 items-center">
              <label className="w-16 text-right text-gray-600">Subject</label>
              <input
                className="flex-1 border border-[#b7c5d9] bg-white px-2 py-0.5 text-xs"
                value={form.title}
                onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                placeholder="Optional"
              />
            </div>
            <div className="flex gap-2 items-start">
              <label className="w-16 text-right text-gray-600 mt-0.5">Comment</label>
              <textarea
                className="flex-1 border border-[#b7c5d9] bg-white px-2 py-0.5 text-xs min-h-[80px]"
                value={form.body}
                onChange={e => setForm(f => ({ ...f, body: e.target.value }))}
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
        )}
      </div>

      <hr className="border-[#b7c5d9] my-3 max-w-4xl mx-auto" />

      {/* Posts */}
      <div className="max-w-4xl mx-auto px-3 space-y-6 pb-10">
        {posts.length === 0 && (
          <p className="text-xs text-gray-500">No posts yet. Be the first to post.</p>
        )}

        {posts.map((post) => (
          <div key={post.id}>
            {/* OP post */}
            <div className="bg-[#f0e0d6] border border-[#d9bfb7] p-2 inline-block max-w-full">
              <div className="text-xs text-gray-600 mb-1 flex gap-3 flex-wrap">
                <span className="text-[#117743] font-bold">Anonymous</span>
                <span>{new Date(post.created_at).toLocaleString()}</span>
                <span className="text-[#34345c]">No.{post.id}</span>
                {post.title && (
                  <span className="text-[#0f0c5d] font-bold">{post.title}</span>
                )}
              </div>
              <p className="text-xs whitespace-pre-wrap break-words max-w-prose">{post.body}</p>
            </div>

            {/* First 2 comments */}
            {post.comments.length > 0 && (
              <div className="ml-8 mt-1 space-y-1">
                {post.comments.slice(0, 2).map((comment) => (
                  <div key={comment.id} className="bg-[#d6daf0] border border-[#b7c5d9] p-2 inline-block max-w-full">
                    <div className="text-xs text-gray-600 mb-1 flex gap-3">
                      <span className="text-[#117743] font-bold">Anonymous</span>
                      <span>{new Date(comment.created_at).toLocaleString()}</span>
                      <span className="text-[#34345c]">No.{comment.id}</span>
                    </div>
                    <p className="text-xs whitespace-pre-wrap break-words max-w-prose">{comment.body}</p>
                  </div>
                ))}

                <div className="text-xs mt-1">
                  {post.comments.length > 2 && (
                    <span className="text-gray-500 mr-2">
                      {post.comments.length - 2} post{post.comments.length - 2 !== 1 ? 's' : ''} omitted.
                    </span>
                  )}
                  <Link
                    href={`/${board.name}/thread/${post.id}`}
                    className="text-[#34345c] hover:text-[#af0a0f] underline font-bold"
                  >
                    {post.comments.length > 2 ? 'See All Replies' : 'Reply'}
                  </Link>
                </div>
              </div>
            )}

            {post.comments.length === 0 && (
              <div className="ml-8 mt-1 text-xs">
                <Link
                  href={`/${board.name}/thread/${post.id}`}
                  className="text-[#34345c] hover:text-[#af0a0f] underline font-bold"
                >
                  [ Reply ]
                </Link>
              </div>
            )}
          </div>
        ))}
      </div>
    </main>
  )
}