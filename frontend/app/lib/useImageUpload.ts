"use client"

import { useState } from "react"
import { useAuth } from "@clerk/nextjs"
import imageCompression from "browser-image-compression"

export const MAX_IMAGES = 5

export type ImageState = {
  file: File
  preview: string
  progress: number
  url: string | null
}

// Gère la compression + l'upload des images vers /upload, plafonné à MAX_IMAGES.
// imagesExistantes : nombre de photos déjà attachées (édition) à déduire du quota.
export function useImageUpload(imagesExistantes = 0) {
  const { getToken } = useAuth()
  const [images, setImages] = useState<ImageState[]>([])
  const [erreur, setErreur] = useState("")

  const uploadEnCours = images.some((img) => img.url === null)
  const slotsRestants = MAX_IMAGES - imagesExistantes - images.length

  // Chaque vignette est identifiée par son preview (URL objet unique),
  // pas par son index : pas de décalage si deux ajouts s'enchaînent.
  function patcher(preview: string, changements: Partial<ImageState>) {
    setImages((prev) => prev.map((img) => (img.preview === preview ? { ...img, ...changements } : img)))
  }

  async function ajouterImages(fichiers: File[]) {
    setErreur("")
    const aTraiter = fichiers.slice(0, Math.max(0, slotsRestants))
    if (aTraiter.length === 0) return

    const nouveaux: ImageState[] = aTraiter.map((file) => ({
      file,
      preview: URL.createObjectURL(file),
      progress: 0,
      url: null,
    }))

    setImages((prev) => [...prev, ...nouveaux])

    for (const nouveau of nouveaux) {
      try {
        const compressed = await imageCompression(nouveau.file, {
          maxSizeMB: 2,
          maxWidthOrHeight: 1920,
          useWebWorker: true,
          onProgress: (progress) => patcher(nouveau.preview, { progress }),
        })

        const formData = new FormData()
        formData.append("files", compressed)

        const token = await getToken()
        const uploadRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/upload`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        })
        if (!uploadRes.ok) {
          const data = await uploadRes.json().catch(() => ({}))
          throw new Error(data.detail || "L'envoi de la photo a échoué")
        }
        const uploadData = await uploadRes.json()
        patcher(nouveau.preview, { url: uploadData.urls[0], progress: 100 })
      } catch (e) {
        // Échec : on retire la vignette et on affiche la raison
        setImages((prev) => prev.filter((img) => img.preview !== nouveau.preview))
        URL.revokeObjectURL(nouveau.preview)
        setErreur(e instanceof Error ? e.message : "L'envoi de la photo a échoué")
      }
    }
  }

  return { images, setImages, ajouterImages, uploadEnCours, slotsRestants, erreur }
}
