import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { AuthProvider } from "@/auth/AuthProvider";
import { ToastProvider } from "@/ui/Toast";

import { AppRoutes } from "./routes";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ToastProvider>
          <AppRoutes />
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
