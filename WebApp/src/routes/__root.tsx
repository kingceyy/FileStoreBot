import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  useNavigate,
} from "@tanstack/react-router";
import { TonConnectUIProvider } from "@tonconnect/ui-react";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

// URL du manifest TON Connect
const TON_MANIFEST_URL =
  "https://filestorebotwebapp.vercel.app/tonconnect-manifest.json";

/**
 * Not Found "intelligent" :
 * Telegram WebApp et certaines redirections renvoient parfois vers des URLs
 * non gérées (ex: /index, /home, query string TG). Au lieu d'afficher un 404
 * brutal, on redirige vers la page d'accueil après un court délai.
 */
function NotFoundComponent() {
  const navigate = useNavigate();
  const [showFallback, setShowFallback] = useState(false);

  useEffect(() => {
    const t1 = setTimeout(() => {
      navigate({ to: "/", replace: true }).catch(() => {});
    }, 250);
    const t2 = setTimeout(() => setShowFallback(true), 2500);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A] px-4">
      <div className="max-w-md text-center">
        <Loader2 className="animate-spin mx-auto mb-4" size={32} color="#0088CC" />
        <p className="text-sm text-[#FFFFF0]/55 font-semibold">
          Redirection vers l'accueil…
        </p>
        {showFallback && (
          <div className="mt-6">
            <Link
              to="/"
              className="inline-flex items-center justify-center rounded-xl bg-[#0088CC] px-5 py-2.5 text-sm font-extrabold text-[#FFFFF0] active:scale-95"
            >
              Retour à l'accueil
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  const router = useRouter();
  console.error(error);
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0A0A0A] px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-extrabold text-[#FFFFF0]">
          Une erreur est survenue
        </h1>
        <p className="mt-2 text-sm text-[#FFFFF0]/55">{error.message}</p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            onClick={() => {
              router.invalidate();
              reset();
            }}
            className="inline-flex items-center justify-center rounded-xl bg-[#0088CC] px-4 py-2 text-sm font-extrabold text-[#FFFFF0] active:scale-95"
          >
            Réessayer
          </button>
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-bold text-[#FFFFF0] active:scale-95"
          >
            Accueil
          </Link>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  return (
    <TonConnectUIProvider manifestUrl={TON_MANIFEST_URL}>
      <QueryClientProvider client={queryClient}>
        <Outlet />
      </QueryClientProvider>
    </TonConnectUIProvider>
  );
}
