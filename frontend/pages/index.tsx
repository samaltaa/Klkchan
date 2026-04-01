import Link from 'next/link'
import { GetServerSideProps } from 'next'
import { getBoards } from '@/api'
import { Board } from '@/types'

interface Props {
  boards: Board[]
}

export default function HomePage({ boards }: Props) {
  const sorted = [...boards].sort((a, b) => a.name.localeCompare(b.name))

  return (
    <main className="min-h-screen bg-[#eef2ff]">
      {/* Header */}
      <header className="bg-[#af0a0f] text-white text-center py-3 border-b-4 border-[#800000]">
        <h1 className="text-2xl font-bold tracking-wide">kkchan</h1>
        <p className="text-xs text-red-200 mt-0.5">the imageboard</p>
      </header>

      <div className="max-w-2xl mx-auto mt-8 px-4">
        <div className="bg-[#d6daf0] border border-[#b7c5d9] p-4 rounded">
          <h2 className="text-[#af0a0f] font-bold text-sm mb-3 border-b border-[#b7c5d9] pb-1">
            Boards
          </h2>

          {sorted.length === 0 && (
            <p className="text-xs text-gray-500">No boards yet.</p>
          )}

          {/* Inline board links */}
          <div className="flex flex-wrap gap-x-1 gap-y-1">
            {sorted.map((board, i) => (
              <span key={board.id} className="text-xs">
                <Link
                  href={`/${board.name}`}
                  className="text-[#34345c] hover:text-[#af0a0f] font-bold underline"
                >
                  /{board.name}/
                </Link>
                {i < sorted.length - 1 && (
                  <span className="text-gray-400 ml-1">-</span>
                )}
              </span>
            ))}
          </div>

          {/* Board list with descriptions */}
          <div className="mt-4 space-y-1">
            {sorted.map((board) => (
              <div key={board.id} className="text-xs">
                <Link
                  href={`/${board.name}`}
                  className="text-[#34345c] hover:text-[#af0a0f] font-bold underline"
                >
                  /{board.name}/
                </Link>
                <span className="text-gray-600 ml-2">— {board.description}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <footer className="text-center text-xs text-gray-400 mt-12 pb-4">
        kkchan — All content is fictional and for testing purposes.
      </footer>
    </main>
  )
}

export const getServerSideProps: GetServerSideProps = async () => {
  try {
    const boards = await getBoards()
    return { props: { boards } }
  } catch (e) {
    return { props: { boards: [] } }
  }
}