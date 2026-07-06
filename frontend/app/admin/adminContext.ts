"use client"

import { createContext, useContext } from "react"

// Rôle fourni par le layout /admin après vérification serveur (GET /admin/moi).
// Purement cosmétique côté client : chaque endpoint re-vérifie le rôle en base.
export const AdminContext = createContext<{ role: string }>({ role: "" })
export const useAdmin = () => useContext(AdminContext)
