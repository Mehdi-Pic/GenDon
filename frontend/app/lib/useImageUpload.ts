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

  const uploadEnCours = images.some((img) => img.url === null)
  const slotsRestants = MAX_IMAGES - imagesExistantes - images.length

  async function ajouterImages(fichiers: File[]) {
    const aTraiter = fichiers.slice(0, Math.max(0, slotsRestants))
    if (aTraiter.length === 0) return

    const nouveaux: ImageState[] = aTraiter.map((file) => ({
      file,
      preview: URL.createObjectURL(file),
      progress: 0,
      url: null,
    }))

    setImages((prev) => [...prev, ...nouveaux])

    const offset = images.length
    for (let i = 0; i < aTraiter.length; i++) {
      const indexGlobal = offset + i

      const compressed = await imageCompression(aTraiter[i], {
        maxSizeMB: 2,
        maxWidthOrHeight: 1920,
        useWebWorker: true,
        onProgress: (progress) => {
          setImages((prev) => {
            const next = [...prev]
            if (next[indexGlobal]) next[indexGlobal] = { ...next[indexGlobal], progress }
            return next
          })
        },
      })

      const formData = new FormData()
      formData.append("files", compressed)

      const token = await getToken()
      const uploadRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })
      const uploadData = await uploadRes.json()

      setImages((prev) => {
        const next = [...prev]
        if (next[indexGlobal]) next[indexGlobal] = { ...next[indexGlobal], url: uploadData.urls[0], progress: 100 }
        return next
      })
    }
  }

  return { images, setImages, ajouterImages, uploadEnCours, slotsRestants }
}
