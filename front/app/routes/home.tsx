import { Button } from '~/components/ui/button';

export function meta() {
  return [
    { title: 'VeloSim' },
    { name: 'description', content: 'Welcome to VeloSim!' },
  ];
}

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center">
      <Button>Start simulation</Button>
    </main>
  );
}
