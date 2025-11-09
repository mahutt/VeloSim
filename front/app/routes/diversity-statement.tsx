/**
 * MIT License
 *
 * Copyright (c) 2025 VeloSim Contributors
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

import { Link } from 'react-router';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '~/components/ui/tabs';
import { Card, CardHeader, CardContent } from '~/components/ui/card';
import { Badge } from '~/components/ui/badge';
import { Separator } from '~/components/ui/separator';
import { ArrowLeft } from 'lucide-react';

export function meta() {
  return [{ title: 'Diversity Statement' }];
}

export default function DiversityStatement() {
  const configContent = {
    en: (
      <>
        <p>
          To support end users with diverse abilities, the interface will follow
          accessibility best practices in order to remain usable by a broad
          range of individuals. For instance, the{' '}
          <a
            href="https://github.com/vinishamanek/VeloSim/wiki/Infrastructure-and-Tools#shadcn-ui"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-800 underline hover:text-blue-600 break-words"
          >
            shadcn UI library
          </a>{' '}
          makes it possible to work with components that already follow{' '}
          <a
            href="https://www.w3.org/WAI/ARIA/apg/patterns/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-800 underline hover:text-blue-600 break-words"
          >
            WAI-ARIA design patterns
          </a>
          . Following release 1, the project also intends to consider end users
          with colour blindness. Map colours, markers, and routes will be
          designed to remain visually distinct, with configurable options that
          account for different types of colour vision deficiencies.
        </p>

        <p className="mt-4">
          Velosim commits to the inclusivity of all users. The team puts
          significant attention into ensuring everyone&apos;s needs and goals
          can be achieved for this simulation. Ease of use for all users is a
          key factor in its design by creating intuitive and simple features.
          The application aims to support users across all their needs, whether
          running a simulation, dispatching resources to tasks, seeking details
          of a specific station, or creating a scenario. In addition, a user
          guide will be made easily accessible for better understanding and
          support for all features.
        </p>

        <p className="mt-4">
          Equity and diversity in the project extend beyond the user-facing
          interface to the way a team collaborates and conducts work. To
          encourage an inclusive and respectful development environment, the
          project could include a{' '}
          <a
            href="https://www.contributor-covenant.org/version/3/0/code_of_conduct/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-800 underline hover:text-blue-600 break-words"
          >
            Code of Conduct
          </a>{' '}
          in the GitHub repository when its visibility becomes public. We hope
          to set clear expectations for professional behaviour and interactions
          among contributors.
        </p>
      </>
    ),
    fr: (
      <>
        <p>
          Pour soutenir les utilisateurs finaux ayant des capacités diverses,
          l&apos;interface graphique suivra les meilleures pratiques en matière
          d&apos;accessibilité afin de rester utilisable par un large éventail
          de personnes. Par exemple,{' '}
          <a
            href="https://github.com/vinishamanek/VeloSim/wiki/Infrastructure-and-Tools#shadcn-ui"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-800 underline hover:text-blue-600 break-words"
          >
            shadcn UI
          </a>{' '}
          permet de travailler avec des composants qui suivent déjà les{' '}
          <a
            href="https://www.w3.org/WAI/ARIA/apg/patterns/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-800 underline hover:text-blue-600 break-words"
          >
            modèles WAI-ARIA
          </a>
          . Suite à la publication de la version 1, le projet prévoit également
          de prendre en compte les utilisateurs daltoniens. Les couleurs de la
          carte, les marqueurs et les itinéraires seront conçus pour rester
          visuellement distincts, avec des options configurables adaptées aux
          différents types de déficiences visuelles.
        </p>

        <p className="mt-4">
          Velosim s&apos;engage en faveur de l&apos;inclusion de tous les
          utilisateurs. L&apos;équipe porte une attention particulière à ce que
          les besoins et objectifs de chacun puissent être atteints pour cette
          simulation. La facilité d&apos;utilisation pour tous les utilisateurs
          est un facteur clé dans sa conception, avec des fonctionnalités
          intuitives et simples. L&apos;application vise à soutenir les
          utilisateurs dans tous leurs besoins, qu&apos;il s&apos;agisse de
          lancer une simulation, d&apos;affecter des ressources à des tâches, de
          consulter les détails d&apos;une station spécifique ou même de créer
          un scénario. De plus, un guide utilisateur sera facilement accessible
          pour mieux comprendre et utiliser toutes les fonctionnalités.
        </p>

        <p className="mt-4">
          L&apos;équité et la diversité dans le projet vont au-delà de
          l&apos;interface utilisateur pour concerner la manière dont
          l&apos;équipe collabore et effectue son travail. Pour encourager un
          environnement de développement inclusif et respectueux, le projet
          pourrait inclure un{' '}
          <a
            href="https://www.contributor-covenant.org/version/3/0/code_of_conduct/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-800 underline hover:text-blue-600 break-words"
          >
            code de conduite
          </a>{' '}
          dans le dépôt GitHub lorsque sa visibilité sera publique. Nous
          espérons définir des attentes claires pour le comportement
          professionnel et les interactions entre contributeurs.
        </p>
      </>
    ),
  };

  const configKeyPoints = ['Inclusivity', 'Equity', 'a11y', 'l10n'];

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-8 max-w-screen-md mx-auto">
      <div className="mb-6">
        <div className="mb-6">
          <Link
            to="/"
            className="inline-flex items-center text-blue-800 hover:text-blue-600 hover:underline"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back to Home
          </Link>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6 gap-4">
        <h1 className="text-3xl font-bold mb-2 sm:mb-0 break-words">
          Diversity Statement
        </h1>
        <div className="flex flex-wrap gap-2">
          {configKeyPoints.map((point) => (
            <Badge
              key={point}
              className="bg-[var(--primary)] text-[var(--primary-foreground)]"
            >
              {point}
            </Badge>
          ))}
        </div>
      </div>

      <Separator className="mb-6" />

      <Tabs defaultValue="en" className="w-full">
        <TabsList className="overflow-x-auto">
          <TabsTrigger value="en">English</TabsTrigger>
          <TabsTrigger value="fr">Français</TabsTrigger>
        </TabsList>

        <TabsContent value="en">
          <Card className="mt-4">
            <CardHeader>
              <h2 className="text-xl font-semibold break-words">
                Our Commitment
              </h2>
            </CardHeader>
            <CardContent>{configContent.en}</CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="fr">
          <Card className="mt-4">
            <CardHeader>
              <h2 className="text-xl font-semibold break-words">
                Notre Engagement
              </h2>
            </CardHeader>
            <CardContent>{configContent.fr}</CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
