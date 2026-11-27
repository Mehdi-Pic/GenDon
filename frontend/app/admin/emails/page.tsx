"use client"

import { useState } from "react"
import { useAuth } from "@clerk/nextjs"
import { Eye, FlaskConical, Send } from "lucide-react"
import { useAdmin } from "../adminContext"

type Email = { sujet: string; titre: string; message: string; bouton_don: boolean }

const VIDE: Email = { sujet: "", titre: "", message: "", bouton_don: true }

const APPEL_AUX_DONS: Email = {
  sujet: "GenDon a besoin de vous",
  titre: "GenDon a besoin de vous",
  message: `Bonjour,

Nous avons besoin de vous pour que GenDon fonctionne.

Si chacun d'entre vous pouvait déposer un don, quelque chose dont vous n'avez pas ou plus l'usage, cela permettrait d'augmenter le nombre d'annonces disponibles.

Merci d'avance pour votre soutien.

L'équipe GenDon`,
  bouton_don: true,
}

export default function AdminEmails() {
  const { role } = useAdmin()
  const { getToken } = useAuth()
  const [email, setEmail] = useState<Email>(VIDE)
  const [apercu, setApercu] = useState<string | null>(null)
  const [destinataires, setDestinataires] = useState<number | null>(null)
  const [testEnvoye, setTestEnvoye] = useState(false)
  const [enCours, setEnCours] = useState(false)
  const [info, setInfo] = useState<{ ok: boolean; texte: string } | null>(null)

  if (role !== "admin") {
    return <p className="text-gray-400 py-12 text-center">Réservé aux administrateurs.</p>
  }

  const modifier = (champs: Partial<Email>) => {
    setEmail((e) => ({ ...e, ...champs }))
    setApercu(null)
    setTestEnvoye(false) // le contenu a changé : le test précédent ne vaut plus
    setInfo(null)
  }

  const appeler = async (chemin: string) => {
    setEnCours(true)
    setInfo(null)
    try {
      const token = await getToken()
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/emails/${chemin}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(email),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        const detail = typeof data.detail === "string" ? data.detail : "Vérifiez les champs (sujet, titre, message assez longs)."
        setInfo({ ok: false, texte: detail })
        return null
      }
      return data
    } catch {
      setInfo({ ok: false, texte: "Serveur injoignable." })
      return null
    } finally {
      setEnCours(false)
    }
  }

  const voirApercu = async () => {
    const data = await appeler("apercu")
    if (data) {
      setApercu(data.html)
      setDestinataires(data.destinataires)
    }
  }

  const envoyerTest = async () => {
    const data = await appeler("test")
    if (data) {
      setTestEnvoye(true)
      setInfo({ ok: true, texte: `Test envoyé à ${data.envoye_a}. Vérifiez votre boîte mail (et les spams).` })
    }
  }

  const envoyerATous = async () => {
    const n = destinataires ?? "tous les"
    if (!window.confirm(`Envoyer « ${email.sujet} » à ${n} inscrits ? Cette action est définitive.`)) return
    const data = await appeler("envoi")
    if (data) {
      setInfo({ ok: true, texte: `Envoi lancé vers ${data.destinataires} inscrits. Il peut prendre quelques minutes.` })
    }
  }

  const champ = "w-full rounded-xl ring-1 ring-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"

  return (
    <div>
      <h1 className="text-xl sm:text-2xl font-black text-gray-900 mb-1">Email aux inscrits</h1>
      <p className="text-sm text-gray-400 mb-6">
        Envoyé à tous les comptes, sauf ceux qui ont désactivé la lettre d&apos;information. Chaque email contient un lien de désabonnement.
      </p>

      <button
        type="button"
        onClick={() => modifier(APPEL_AUX_DONS)}
        className="mb-5 text-sm font-semibold text-green-700 hover:underline"
      >
        Remplir avec le modèle « Appel aux dons »
      </button>

      <div className="flex flex-col gap-4">
        <label className="block">
          <span className="block text-sm font-semibold text-gray-700 mb-1">Objet de l&apos;email</span>
          <input className={champ} maxLength={150} value={email.sujet} onChange={(e) => modifier({ sujet: e.target.value })} />
        </label>
        <label className="block">
          <span className="block text-sm font-semibold text-gray-700 mb-1">Titre (en haut de l&apos;email)</span>
          <input className={champ} maxLength={120} value={email.titre} onChange={(e) => modifier({ titre: e.target.value })} />
        </label>
        <label className="block">
          <span className="block text-sm font-semibold text-gray-700 mb-1">Message</span>
          <textarea
            className={`${champ} min-h-[220px]`}
            maxLength={5000}
            value={email.message}
            onChange={(e) => modifier({ message: e.target.value })}
          />
          <span className="block text-xs text-gray-400 mt-1">Une ligne vide sépare deux paragraphes.</span>
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={email.bouton_don} onChange={(e) => modifier({ bouton_don: e.target.checked })} />
          Ajouter le bouton « Déposer un don »
        </label>
      </div>

      <div className="flex flex-wrap gap-2 mt-6">
        <button
          type="button"
          onClick={voirApercu}
          disabled={enCours}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-semibold ring-1 ring-gray-200 hover:bg-gray-50 disabled:opacity-50"
        >
          <Eye className="w-4 h-4" /> Aperçu
        </button>
        <button
          type="button"
          onClick={envoyerTest}
          disabled={enCours}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-semibold ring-1 ring-gray-200 hover:bg-gray-50 disabled:opacity-50"
        >
          <FlaskConical className="w-4 h-4" /> M&apos;envoyer un test
        </button>
        <button
          type="button"
          onClick={envoyerATous}
          disabled={enCours || !testEnvoye}
          title={testEnvoye ? undefined : "Envoyez-vous d'abord un test"}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-semibold bg-green-600 text-white hover:bg-green-700 disabled:opacity-40"
        >
          <Send className="w-4 h-4" /> Envoyer à {destinataires ?? "tous les"} inscrits
        </button>
      </div>
      {!testEnvoye && <p className="text-xs text-gray-400 mt-2">L&apos;envoi à tous est possible après un test sur votre adresse.</p>}

      {info && <p className={`mt-4 text-sm ${info.ok ? "text-green-700" : "text-red-600"}`}>{info.texte}</p>}

      {apercu && (
        <div className="mt-6">
          <p className="text-sm font-semibold text-gray-700 mb-2">Aperçu</p>
          <iframe
            title="Aperçu de l'email"
            srcDoc={apercu}
            sandbox=""
            className="w-full h-[560px] rounded-2xl ring-1 ring-gray-200 bg-white"
          />
        </div>
      )}
    </div>
  )
}
