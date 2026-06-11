import Link from "next/link"

export default function Footer() {
  return (
    <footer className="border-t border-gray-100 bg-gray-50/60 mt-16">
      <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        <p className="text-sm text-gray-400">
          © {new Date().getFullYear()} <span className="font-semibold text-gray-600">Gen<span className="text-green-600">Don</span></span> · Dons gratuits entre habitants de Gennevilliers
        </p>
        <nav className="flex items-center gap-6">
          <Link href="/mentions-legales" className="text-sm text-gray-400 hover:text-gray-900 transition-colors">
            Mentions légales
          </Link>
          <Link href="/confidentialite" className="text-sm text-gray-400 hover:text-gray-900 transition-colors">
            Confidentialité
          </Link>
        </nav>
      </div>
    </footer>
  )
}
