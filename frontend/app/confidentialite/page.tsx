import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Politique de confidentialité · Gen Don",
  description: "Politique de confidentialité du site GenDon : données collectées, finalités et droits RGPD.",
}

export default function Confidentialite() {
  return (
    <main>
      <div className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-black text-gray-900 mb-2">Politique de confidentialité</h1>
        <p className="text-sm text-gray-400 mb-10">Dernière mise à jour : juin 2026</p>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Responsable du traitement</h2>
          <p className="text-gray-600 leading-relaxed">
            Le responsable du traitement des données collectées sur <strong>gendon.fr</strong> est
            l&apos;éditeur du site : Mehdi Pichard,{" "}
            <a href="mailto:pichardmehdi@gmail.com" className="text-green-600 hover:underline">pichardmehdi@gmail.com</a>.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Données collectées</h2>
          <ul className="list-disc pl-5 text-gray-600 leading-relaxed flex flex-col gap-2">
            <li>
              <strong>Compte utilisateur</strong> : adresse email, nom d&apos;utilisateur et/ou prénom,
              collectés lors de l&apos;inscription via notre prestataire d&apos;authentification Clerk.
            </li>
            <li>
              <strong>Annonces</strong> : titre, description, catégorie, quartier, photos et pseudo
              affichés publiquement sur le site.
            </li>
            <li>
              <strong>Messages de contact</strong> : lorsque vous contactez un donneur, votre message et
              votre adresse email sont transmis par email au donneur afin qu&apos;il puisse vous répondre.
              Les messages ne sont pas conservés par GenDon.
            </li>
          </ul>
          <p className="text-gray-600 leading-relaxed mt-3">
            Aucune donnée n&apos;est revendue ni utilisée à des fins publicitaires.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Finalités et base légale</h2>
          <p className="text-gray-600 leading-relaxed">
            Les données sont traitées uniquement pour faire fonctionner le service : création et gestion
            du compte, publication des annonces, mise en relation entre donneurs et intéressés. La base
            légale est l&apos;exécution du service demandé par l&apos;utilisateur (art. 6.1.b du RGPD).
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Sous-traitants</h2>
          <ul className="list-disc pl-5 text-gray-600 leading-relaxed flex flex-col gap-2">
            <li><strong>Clerk Inc.</strong> (États-Unis) : authentification et gestion des comptes.</li>
            <li><strong>Cloudinary Ltd.</strong> : hébergement des photos d&apos;annonces.</li>
            <li><strong>Resend Inc.</strong> (États-Unis) : envoi des emails de mise en relation.</li>
            <li><strong>Vercel Inc.</strong> et <strong>Railway Corp.</strong> (États-Unis) : hébergement du site et de la base de données.</li>
          </ul>
          <p className="text-gray-600 leading-relaxed mt-3">
            Ces prestataires peuvent être situés hors de l&apos;Union européenne ; ils s&apos;appuient sur
            des clauses contractuelles types pour encadrer les transferts de données.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Durées de conservation</h2>
          <ul className="list-disc pl-5 text-gray-600 leading-relaxed flex flex-col gap-2">
            <li>Les <strong>annonces</strong> (textes et photos) sont automatiquement supprimées <strong>30 jours</strong> après leur publication, ou dès leur suppression par l&apos;utilisateur.</li>
            <li>Le <strong>compte utilisateur</strong> est conservé tant qu&apos;il est actif ; sa suppression peut être demandée à tout moment.</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Vos droits</h2>
          <p className="text-gray-600 leading-relaxed">
            Conformément au RGPD, vous disposez d&apos;un droit d&apos;accès, de rectification,
            d&apos;effacement, de limitation et d&apos;opposition sur vos données. Pour exercer ces
            droits, écrivez à{" "}
            <a href="mailto:pichardmehdi@gmail.com" className="text-green-600 hover:underline">pichardmehdi@gmail.com</a>.
            Vous pouvez également introduire une réclamation auprès de la CNIL (<a href="https://www.cnil.fr" className="text-green-600 hover:underline" target="_blank" rel="noopener noreferrer">cnil.fr</a>).
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">Cookies</h2>
          <p className="text-gray-600 leading-relaxed">
            GenDon n&apos;utilise pas de cookies publicitaires ni de traceurs tiers. Seuls des cookies
            strictement nécessaires au fonctionnement du site sont déposés (session
            d&apos;authentification Clerk), exemptés de consentement au titre de la réglementation.
          </p>
        </section>
      </div>
    </main>
  )
}
