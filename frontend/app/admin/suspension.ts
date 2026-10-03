// Suspension d'un compte (bannissement Clerk) : partagé par la liste des utilisateurs
// et la lecture d'une conversation signalée. Renvoie true si le serveur a appliqué le changement.
export async function changerSuspension(
  getToken: () => Promise<string | null>,
  uid: string,
  pseudo: string,
  suspendu: boolean,
): Promise<boolean> {
  const question = suspendu
    ? `Suspendre le compte de ${pseudo} ? Ses sessions sont fermées et il ne pourra plus se connecter.`
    : `Réactiver le compte de ${pseudo} ?`
  if (!confirm(question)) return false
  try {
    const token = await getToken()
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/utilisateurs/${uid}/suspendre`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ suspendu }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      alert(data.detail || "L'opération a échoué.")
      return false
    }
    return true
  } catch {
    alert("L'opération a échoué.")
    return false
  }
}
