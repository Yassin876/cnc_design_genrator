import React, { useEffect, useRef } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './app/routes/AppLayout';

const queryClient = new QueryClient();

export const App: React.FC = () => {
  const startupTimeRef = useRef(performance.now());
  console.log('[Startup] App component mounted at', startupTimeRef.current);

  useEffect(() => {
    const fullLoadMs = performance.now() - startupTimeRef.current;
    console.log(`[Startup] Full app load: ${fullLoadMs.toFixed(1)}ms`);
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <AppLayout />
    </QueryClientProvider>
  );
};

export default App;
