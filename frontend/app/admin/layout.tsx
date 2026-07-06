"use client"

import { useEffect, useState } from "react"
import { useAuth } from "@clerk/nextjs"
import { notFound, usePathname } from "next/navigation"
import Link from "next/link"
import { LayoutDashboard, ClipboardList, Users, Flag, ScrollText, ShieldCheck } from "lucide-react"
import { AdminContext } from "./adminContext"

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const pathname = usePathname()
  const [role, setRole] = useState<string>("")
  const [etat, setEtat] = useState<"chargement" | "ok" | "refuse">("chargement")

  useEffect(() => {
    if (!isLoaded) return
    if (!isSignedIn) {
      setEtat("refuse")
      return
    }
    let actif = true
    ;(async () => {
      try {
        const token = await getToken()
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/moi`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!actif) return
        if (!res.ok) {
          setEtat("refuse")
          return
        }
        const data = await res.json()
        setRole(data.role)
        setEtat("ok")
      } catch {
        if (actif) setEtat("refuse")
      }
    })()
    return () => { actif = false }
  }, [isLoaded, isSignedIn, getToken])

  if (etat === "chargement") {
    return (
      <main>
        <div className="max-w-6xl mx-auto px-6 py-12">
          <p className="text-gray-400">Chargement...</p>
        </div>
      </main>
    )
  }

  // Pour un visiteur non autorisé, la page n'existe pas.
  if (etat === "refuse") notFound()

  const liens = [
    { href: "/admin", label: "Tableau de bord", Icon: LayoutDashboard },
    { href: "/admin/annonces", label: "Annonces", Icon: ClipboardList },
    { href: "/admin/utilisateurs", label: "Utilisateurs", Icon: Users },
    { href: "/admin/signalements", label: "Signalements", Icon: Flag },
    ...(role === "admin" ? [{ href: "/admin/journal", label: "Journal", Icon: ScrollText }] : []),
  ]

  return (
    <AdminContext.Provider value={{ role }}>
      <main>
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 flex flex-col md:flex-row gap-6 md:gap-10">
          <aside className="md:w-56 shrink-0">
            <div className="flex items-center gap-2 mb-4 px-2">
              <ShieldCheck className="w-5 h-5 text-green-600" />
              <div>
                <p className="font-bold text-gray-900 leading-tight">Administration</p>
                <p className="text-xs text-gray-400 capitalize">{role === "admin" ? "Administrateur" : "Modérateur"}</p>
              </div>
            </div>
            <nav className="flex md:flex-col gap-1 overflow-x-auto no-scrollbar">
              {liens.map(({ href, label, Icon }) => {
                const actif = href === "/admin" ? pathname === "/admin" : pathname.startsWith(href)
                return (
                  <Link
                    key={href}
                    href={href}
                    className={`flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition-colors ${
                      actif ? "bg-gray-900 text-white" : "text-gray-600 hover:bg-gray-50"
                    }`}
                  >
                    <Icon className="w-4 h-4 shrink-0" />
                    {label}
                  </Link>
                )
              })}
            </nav>
          </aside>
          <section className="flex-1 min-w-0">{children}</section>
        </div>
      </main>
    </AdminContext.Provider>
  )
}
