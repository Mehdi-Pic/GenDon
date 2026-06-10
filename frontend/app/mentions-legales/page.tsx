import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Mentions légales · Gen Don",
  description: "Mentions légales du site GenDon, plateforme de dons entre habitants de Gennevilliers.",
}

export default function MentionsLegales() {
  return (
    <main>
      <div className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-black text-gray-900 mb-2">Mentions légales</h1>
        <p className="text-sm text-gray-400 mb-10">Dernière mise à jour : juin 2026</p>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Éditeur du site</h2>
          <p className="text-gray-600 leading-relaxed">
            Le site <strong>gendon.fr</strong> (« GenDon ») est un service non commercial de mise en
            relation entre habitants de Gennevilliers pour le don d&apos;objets.
          </p>
          <p className="text-gray-600 leading-relaxed mt-2">
            Éditeur : Mehdi Pichard<br />
            Contact : <a href="mailto:pichardmehdi@gmail.com" className="text-green-600 hover:underline">pichardmehdi@gmail.com</a>
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Hébergement</h2>
          <p className="text-gray-600 leading-relaxed">
            Le site est hébergé par <strong>Vercel Inc.</strong>, 340 S Lemon Ave #4133, Walnut, CA 91789,
            États-Unis (<a href="https://vercel.com" className="text-green-600 hover:underline" target="_blank" rel="noopener noreferrer">vercel.com</a>).
          </p>
          <p className="text-gray-600 leading-relaxed mt-2">
            Les services applicatifs et la base de données sont hébergés par <strong>Railway Corp.</strong>,
            San Francisco, Californie, États-Unis (<a href="https://railway.com" className="text-green-600 hover:underline" target="_blank" rel="noopener noreferrer">railway.com</a>).
          </p>
          <p className="text-gray-600 leading-relaxed mt-2">
            Le nom de domaine est enregistré auprès de <strong>OVH SAS</strong>, 2 rue Kellermann,
            59100 Roubaix, France.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Nature du service</h2>
          <p className="text-gray-600 leading-relaxed">
            GenDon permet aux habitants de Gennevilliers de proposer gratuitement des objets au don et
            de se mettre en relation. Aucune transaction financière n&apos;est réalisée via le site :
            les échanges sont gratuits, entre particuliers, et s&apos;effectuent sous leur seule
            responsabilité. GenDon n&apos;intervient pas dans la remise des objets et ne garantit ni
            leur état ni leur conformité.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Contenus publiés par les utilisateurs</h2>
          <p className="text-gray-600 leading-relaxed">
            Les annonces (textes et photos) sont publiées par les utilisateurs, qui en demeurent seuls
            responsables. En publiant une annonce, l&apos;utilisateur garantit disposer des droits sur
            les contenus mis en ligne et s&apos;engage à ne publier aucun contenu illicite, contrefaisant
            ou contraire à l&apos;ordre public. Tout contenu signalé comme illicite pourra être retiré.
            Les annonces sont automatiquement supprimées 30 jours après leur publication.
          </p>
          <p className="text-gray-600 leading-relaxed mt-2">
            Pour signaler un contenu : <a href="mailto:pichardmehdi@gmail.com" className="text-green-600 hover:underline">pichardmehdi@gmail.com</a>
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-3">Propriété intellectuelle</h2>
          <p className="text-gray-600 leading-relaxed">
            La structure du site, son design et ses éléments graphiques sont la propriété de
            l&apos;éditeur. Les photos et textes des annonces restent la propriété de leurs auteurs.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-3">Données personnelles</h2>
          <p className="text-gray-600 leading-relaxed">
            Le traitement des données personnelles est détaillé dans la{" "}
            <a href="/confidentialite" className="text-green-600 hover:underline">politique de confidentialité</a>.
          </p>
        </section>
      </div>
    </main>
  )
}
