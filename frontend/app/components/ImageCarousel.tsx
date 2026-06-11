"use client"

import { useState } from "react"
import { ChevronLeft, ChevronRight, X } from "lucide-react"
import { vignette } from "../lib/annonces"

export default function ImageCarousel({ images }: { images: string[] }) {
  const [index, setIndex] = useState(0)
  const [imageAgrandie, setImageAgrandie] = useState<string | null>(null)

  if (!images || images.length === 0) {
    return (
      <div className="w-full h-80 bg-gray-100 flex items-center justify-center rounded-2xl mb-8">
        <span className="text-gray-400">Pas de photo</span>
      </div>
    )
  }

  function precedent() {
    setIndex((prev) => (prev === 0 ? images.length - 1 : prev - 1))
  }

  function suivant() {
    setIndex((prev) => (prev === images.length - 1 ? 0 : prev + 1))
  }

  return (
    <>
      {imageAgrandie && (
        <div onClick={() => setImageAgrandie(null)} className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-16">
          <button onClick={() => setImageAgrandie(null)} className="absolute top-4 right-4 bg-white/20 hover:bg-white/30 rounded-full p-2 transition-colors">
            <X className="w-6 h-6 text-white" />
          </button>
          <img src={imageAgrandie} alt="agrandie" className="max-w-full max-h-full object-contain rounded-xl" />
        </div>
      )}
      <div className="mb-8">
        <div className="relative rounded-3xl overflow-hidden mb-3 bg-gray-50 ring-1 ring-gray-100">
          <img src={images[index]} alt={`Photo ${index + 1}`} onClick={() => setImageAgrandie(images[index])} className="w-full h-80 object-contain bg-gray-50 cursor-pointer" />
          {images.length > 1 && (
            <>
              <button onClick={precedent} className="absolute left-3 top-1/2 -translate-y-1/2 bg-white/80 hover:bg-white rounded-full p-2 transition-colors" aria-label="Image précédente">
                <ChevronLeft className="w-5 h-5 text-gray-700" />
              </button>
              <button onClick={suivant} className="absolute right-3 top-1/2 -translate-y-1/2 bg-white/80 hover:bg-white rounded-full p-2 transition-colors" aria-label="Image suivante">
                <ChevronRight className="w-5 h-5 text-gray-700" />
              </button>
            </>
          )}
        </div>
        {images.length > 1 && (
          <div className="flex items-center justify-center gap-2">
            {images.map((img, i) => (
              <button key={i} onClick={() => setIndex(i)} className={`w-16 h-16 rounded-xl overflow-hidden border-2 transition-all ${i === index ? "border-green-500 opacity-100" : "border-transparent opacity-60 hover:opacity-100"}`}>
                <img src={vignette(img, 200)} alt={`Miniature ${i + 1}`} className="w-full h-full object-cover" />
              </button>
            ))}
          </div>
        )}
      </div>
    </>
  )
}