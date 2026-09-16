import React, { useEffect, Component, lazy, Suspense } from 'react';
import { useWorkspaceStore } from '../store/useWorkspaceStore';
import { useAuthStore } from '../store/useAuthStore';
import { AppSidebar } from '../../components/layout/AppSidebar';
import { DesktopHeader } from '../../components/layout/DesktopHeader';
import { StatusBar } from '../../components/layout/StatusBar';
import { AuthPage } from '../../features/auth/AuthPage';
import { ExportDialog } from '../../components/dialogs/ExportDialog';
import { ValidationDialog } from '../../components/dialogs/ValidationDialog';
import { ImportDialog } from '../../components/dialogs/ImportDialog';
import { NewProjectDialog } from '../../components/dialogs/NewProjectDialog';
import { AuthModal } from '../../components/dialogs/AuthModal';
import { VersionHistoryModal } from '../../components/dialogs/VersionHistoryModal';
import { NestingDialog } from '../../components/dialogs/NestingDialog';
import { GenerationProgressPanel } from '../../components/generation/GenerationProgressPanel';

const Viewport3D = lazy(() => import('../../features/workspace/3d/Viewport3D').then((m) => ({ default: m.Viewport3D })));
const Canvas2D = lazy(() => import('../../features/workspace/2d/Canvas2D').then((m) => ({ default: m.Canvas2D })));
const AIAssistantSidebar = lazy(() =>
  import('../../features/workspace/ai/AIAssistantSidebar').then((m) => ({ default: m.AIAssistantSidebar }))
);
const PropertiesInspector = lazy(() =>
  import('../../features/workspace/inspector/PropertiesInspector').then((m) => ({ default: m.PropertiesInspector }))
);

const HomeView = lazy(() => import('../../features/dashboard/HomeView'));
const ProjectsView = lazy(() => import('../../features/dashboard/ProjectsView'));
const RecentView = lazy(() => import('../../features/dashboard/RecentView'));
const TemplatesView = lazy(() => import('../../features/dashboard/TemplatesView'));
const TrashView = lazy(() => import('../../features/dashboard/TrashView'));
const FavoritesView = lazy(() => import('../../features/dashboard/FavoritesView'));
const NestingStudio = lazy(() =>
  import('../../features/manufacturing/NestingStudio').then((m) => ({ default: m.NestingStudio }))
);
const SettingsView = lazy(() => import('../../features/settings/SettingsView').then((m) => ({ default: m.SettingsView })));
const BillingView = lazy(() => import('../../features/settings/BillingView').then((m) => ({ default: m.BillingView })));

const ViewLoadingFallback: React.FC = () => (
  <div className="flex-1 flex items-center justify-center bg-[#F8FAFC] text-slate-500 text-sm font-medium">
    Loading…
  </div>
);

const WorkspaceLoadingFallback: React.FC = () => (
  <div className="flex-1 flex items-center justify-center bg-slate-100 text-slate-500 text-sm font-medium">
    Loading workspace…
  </div>
);

// Error Boundary for components
class ErrorBoundary extends Component<{children: React.ReactNode; componentName: string}, {hasError: boolean; error: Error | null}> {
  constructor(props: {children: React.ReactNode; componentName: string}) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error(`[ErrorBoundary] Component ${this.props.componentName} failed:`, error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="w-full h-full flex items-center justify-center bg-red-50 text-red-900">
          <div className="text-center">
            <p className="font-semibold">Error loading {this.props.componentName}</p>
            <p className="text-sm text-red-700 mt-2">{this.state.error?.message}</p>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}


export const AppLayout: React.FC = () => {
  const { viewMode, setViewMode, isVersionHistoryModalOpen, setVersionHistoryModalOpen } = useWorkspaceStore();
  const { isAuthenticated, initializeAuth } = useAuthStore();
  const authInitRef = React.useRef(false);

  // Initialize auth ONCE on mount - don't check isAuthenticated in deps
  useEffect(() => {
    console.log('[Startup] AppLayout mounted at', performance.now());
    if (!authInitRef.current) {
      authInitRef.current = true;
      // Initialize auth in background without blocking UI
      initializeAuth().catch(err => {
        console.error('[Startup] Auth initialization failed:', err);
      });
    }
  }, [initializeAuth]);

  // Show AuthPage immediately if not authenticated
  if ((viewMode as string) === 'auth' || !isAuthenticated) {
    console.log('[Startup] Rendering AuthPage at', performance.now());
    return <AuthPage />;
  }

  // 3D & 2D CAD Workspaces with CAD Header & Status Bar
  if (viewMode === 'workspace_3d' || viewMode === 'workspace_2d') {
    return (
      <div className="w-screen h-screen flex flex-col bg-slate-100 text-slate-900 overflow-hidden font-sans select-none">
        <DesktopHeader />
        <main className="flex-1 flex overflow-hidden relative">
          <Suspense fallback={<WorkspaceLoadingFallback />}>
            <AIAssistantSidebar />
            {viewMode === 'workspace_3d' ? <Viewport3D /> : <Canvas2D />}
            <PropertiesInspector />
          </Suspense>
          <GenerationProgressPanel />
        </main>
        <StatusBar />
        <ExportDialog />
        <ValidationDialog />
        <ImportDialog />
        <NewProjectDialog />
        <AuthModal />
        <NestingDialog />
        <VersionHistoryModal
          isOpen={isVersionHistoryModalOpen}
          onClose={() => setVersionHistoryModalOpen(false)}
        />
      </div>
    );
  }

  // Dashboard & SaaS Views with Left AppSidebar (Matching Screenshots 1-5)
  return (
    <div className="w-screen h-screen flex bg-[#F8FAFC] text-slate-900 overflow-hidden font-sans select-none">
      
      {/* Left Sidebar */}
      <AppSidebar />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        <ErrorBoundary componentName="Dashboard View">
          <Suspense fallback={<ViewLoadingFallback />}>
            {(viewMode === 'home' || viewMode === 'dashboard') && <HomeView />}
            {viewMode === 'projects' && <ProjectsView />}
            {viewMode === 'recent' && <RecentView />}
            {viewMode === 'templates' && <TemplatesView />}
            {viewMode === 'favorites' && <FavoritesView />}

            {viewMode === 'trash' && <TrashView />}
            {viewMode === 'nesting' && <NestingStudio />}
            {viewMode === 'settings' && <SettingsView />}
            {viewMode === 'billing' && <BillingView />}
          </Suspense>
        </ErrorBoundary>

        <GenerationProgressPanel />
      </main>

      {/* Global Modals */}
      <ExportDialog />
      <ValidationDialog />
      <ImportDialog />
      <NewProjectDialog />
      <AuthModal />
      <NestingDialog />
      <VersionHistoryModal
        isOpen={isVersionHistoryModalOpen}
        onClose={() => setVersionHistoryModalOpen(false)}
      />
    </div>
  );
};

export default AppLayout;
