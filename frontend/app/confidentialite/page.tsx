import type { Metadata } from "next"
import Link from "next/link"
import AdresseProtegee from "../components/AdresseProtegee"

export const metadata: Metadata = {
  title: "Politique de confidentialité · Gen Don",
  description: "Politique de confidentialité du site GenDon : données collectées, finalités et droits RGPD.",
}

export default function Confidentialite() {
  return (
    <main>
      <div className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-black text-gray-900 mb-2">Politique de confidentialité</h1>
        <p className="text-sm text-gray-400 mb-10">Dernière mise à jour : octobre 2026</p>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Responsable du traitement</h2>
          <p className="text-gray-600 leading-relaxed">
            Le responsable du traitement des données collectées sur <strong>gendon.fr</strong> est
            l&apos;éditeur du site : Mehdi Pichard, joignable via le{" "}
            <Link href="/contact" className="text-green-600 hover:underline">formulaire de contact</Link> ou par e-mail (<AdresseProtegee />).
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
              <strong>Lettre d&apos;information</strong> : votre adresse email est utilisée pour vous envoyer,
              chaque semaine, un récapitulatif des derniers dons publiés. Vous pouvez vous désabonner à tout
              moment via le lien présent en bas de chaque envoi ou depuis Mon profil, sans que cela affecte votre compte.
            </li>
            <li>
              <strong>Messagerie</strong> : les messages échangés entre un donneur et un intéressé sont
              conservés par GenDon pour permettre la conversation, y compris après le retrait de
              l&apos;annonce, le temps de finaliser la remise de l&apos;objet. Vos adresses email ne sont
              jamais communiquées à l&apos;autre personne. Un email vous prévient d&apos;un nouveau message ;
              vous pouvez le désactiver depuis Mon profil.
            </li>
            <li>
              <strong>Alertes de recherche</strong> : les critères que vous enregistrez (mot-clé, catégorie,
              quartier) servent à vous envoyer par email les nouveaux dons correspondants. Vous les
              supprimez à tout moment depuis Mon profil.
            </li>
            <li>
              <strong>Favoris et signalements</strong> : les annonces que vous mettez en favori, et les
              signalements que vous envoyez (motif et identifiant de votre compte) pour permettre leur traitement.
              Lorsqu&apos;un participant signale une conversation, l&apos;équipe de modération peut lire
              cette conversation, et elle seule, pour traiter le signalement.
            </li>
            <li>
              <strong>Formulaire de contact</strong> : nom, adresse email, sujet et message. Ils ne sont pas
              stockés sur le site : ils sont transmis par email à l&apos;équipe (administrateurs et
              modérateurs) pour vous répondre.
            </li>
            <li>
              <strong>Données techniques</strong> : votre adresse IP est utilisée, en mémoire uniquement et
              pendant 24 heures au plus, pour limiter les abus (envois répétés) et ne compter qu&apos;une vue
              par visiteur sur une annonce. Elle n&apos;est pas enregistrée en base de données. Nos hébergeurs
              conservent par ailleurs des journaux techniques pour la sécurité du service.
            </li>
            <li>
              <strong>Mesure d&apos;audience</strong> : le site utilise Vercel Web Analytics pour compter les
              pages vues de façon agrégée. Cet outil ne dépose aucun cookie et ne permet pas de vous suivre
              d&apos;un site à l&apos;autre ni d&apos;un jour à l&apos;autre.
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
          <p className="text-gray-600 leading-relaxed mt-3">
            La modération (signalements, retrait de contenus), la lutte contre les abus, la mesure
            d&apos;audience et les réponses au formulaire de contact reposent sur l&apos;intérêt légitime
            de GenDon à assurer un service sûr et à vous répondre (art. 6.1.f du RGPD).
          </p>
          <p className="text-gray-600 leading-relaxed mt-3">
            La lettre d&apos;information hebdomadaire repose sur l&apos;intérêt légitime de GenDon à faire
            connaître les dons disponibles à ses membres (art. 6.1.f du RGPD). Vous pouvez vous y opposer
            à tout moment, sans justification, via le lien de désabonnement présent dans chaque envoi
            ou depuis Mon profil.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Sous-traitants</h2>
          <ul className="list-disc pl-5 text-gray-600 leading-relaxed flex flex-col gap-2">
            <li><strong>Clerk Inc.</strong> (États-Unis) : authentification et gestion des comptes.</li>
            <li><strong>Cloudinary Ltd.</strong> (Israël, serveurs aux États-Unis) : hébergement des photos d&apos;annonces.</li>
            <li><strong>Resend Inc.</strong> (États-Unis) : envoi des emails (notifications de messages, alertes de recherche, rappels d&apos;expiration, lettre d&apos;information).</li>
            <li><strong>Vercel Inc.</strong> et <strong>Railway Corp.</strong> (États-Unis) : hébergement du site et de la base de données, mesure d&apos;audience (Vercel).</li>
          </ul>
          <p className="text-gray-600 leading-relaxed mt-3">
            Au sein de l&apos;équipe, les modérateurs bénévoles voient les annonces, les signalements et les
            pseudos des comptes, mais pas leurs adresses email, réservées aux administrateurs. Ni les uns ni
            les autres n&apos;ont accès aux conversations privées, sauf à une conversation signalée par
            l&apos;un de ses participants : chaque lecture est alors inscrite au journal de modération.
            En cas d&apos;abus, l&apos;équipe peut suspendre un compte.
          </p>
          <p className="text-gray-600 leading-relaxed mt-3">
            Ces prestataires peuvent être situés hors de l&apos;Union européenne ; ils s&apos;appuient sur
            des clauses contractuelles types pour encadrer les transferts de données.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Durées de conservation</h2>
          <ul className="list-disc pl-5 text-gray-600 leading-relaxed flex flex-col gap-2">
            <li>Les <strong>annonces</strong> (textes et photos) sont automatiquement supprimées <strong>30 jours</strong> après leur publication (ou leur dernier renouvellement), <strong>3 jours</strong> après avoir été déclarées données, ou dès leur suppression par l&apos;utilisateur.</li>
            <li>Les <strong>photos envoyées mais jamais publiées</strong> sont supprimées sous 48 heures.</li>
            <li>Les <strong>conversations</strong> sont supprimées lorsque les deux participants les ont quittées, ou <strong>30 jours</strong> après le dernier message une fois l&apos;annonce retirée. Une conversation signalée est conservée jusqu&apos;au traitement du signalement.</li>
            <li>À la suppression du compte, les dons réalisés restent comptabilisés de façon anonyme (sans lien avec votre compte ni titre d&apos;annonce).</li>
            <li>Le <strong>journal de modération</strong> (actions de l&apos;équipe, pouvant citer un pseudo ou un titre d&apos;annonce) est conservé <strong>1 an</strong>.</li>
            <li>Les <strong>messages du formulaire de contact</strong> sont conservés dans la boîte email de l&apos;équipe le temps de traiter la demande.</li>
            <li>Le <strong>compte utilisateur</strong> est conservé tant qu&apos;il est actif. Vous pouvez le supprimer vous-même à tout moment (menu du compte en haut à droite, « Gérer le compte ») : vos annonces, photos, messages, favoris, alertes et signalements sont alors effacés.</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Vos droits</h2>
          <p className="text-gray-600 leading-relaxed">
            Conformément au RGPD, vous disposez d&apos;un droit d&apos;accès, de rectification,
            d&apos;effacement, de limitation, d&apos;opposition et de portabilité sur vos données. Pour exercer ces
            droits, utilisez le{" "}
            <Link href="/contact" className="text-green-600 hover:underline">formulaire de contact</Link> ou écrivez par e-mail (<AdresseProtegee />).
            Vous pouvez également introduire une réclamation auprès de la CNIL (<a href="https://www.cnil.fr" className="text-green-600 hover:underline" target="_blank" rel="noopener noreferrer">cnil.fr</a>).
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">Cookies</h2>
          <p className="text-gray-600 leading-relaxed">
            GenDon n&apos;utilise pas de cookies publicitaires. Seuls des cookies strictement nécessaires au
            fonctionnement du site sont déposés (session d&apos;authentification Clerk), exemptés de
            consentement au titre de la réglementation. La mesure d&apos;audience (Vercel Web Analytics)
            fonctionne sans cookie.
          </p>
        </section>
      </div>
    </main>
  )
}
