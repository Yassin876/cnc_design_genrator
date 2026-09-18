import React from 'react';
import { Hexagon, Sparkles, Box, ArrowUpRight, CheckCircle2, Layers, Cpu, Compass, Sliders, Download, Eye } from 'lucide-react';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';

export const LandingPage: React.FC = () => {
  const { setViewMode } = useWorkspaceStore();

  return (
    <div className="w-full h-full min-h-screen bg-[#F8FAFC] text-slate-900 font-sans select-none overflow-y-auto">
      
      {/* 1. Header Navigation Bar */}
      <header className="sticky top-0 z-50 bg-[#F8FAFC]/90 backdrop-blur-md border-b border-slate-200/80 px-8 py-4 flex items-center justify-between">
        
        {/* Logo */}
        <div
          onClick={() => setViewMode('auth')}
          className="flex items-center space-x-2 cursor-pointer group"
        >
          <Hexagon className="w-6 h-6 text-indigo-600 group-hover:rotate-12 transition-transform" />
          <span className="text-lg font-black tracking-tight text-slate-900">CAD Studio</span>
        </div>

        {/* Center Nav Links */}
        <nav className="hidden md:flex items-center space-x-8 text-xs font-semibold text-slate-600">
          <a href="#product" className="hover:text-slate-900 transition-colors">Product</a>
          <a href="#features" className="hover:text-slate-900 transition-colors">Features</a>
          <a href="#use-cases" className="hover:text-slate-900 transition-colors">Use Cases</a>
          <a href="#docs" className="hover:text-slate-900 transition-colors">Docs</a>
        </nav>

        {/* Right Actions */}
        <div className="flex items-center space-x-4 text-xs font-bold">
          <button
            onClick={() => setViewMode('auth')}
            className="text-slate-700 hover:text-slate-900 transition-colors px-3 py-2"
          >
            Log in
          </button>
          <button
            onClick={() => setViewMode('auth')}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl shadow-md shadow-blue-600/20 transition-all"
          >
            Get Started
          </button>
        </div>

      </header>

      {/* 2. Hero Section */}
      <section className="max-w-5xl mx-auto px-6 pt-16 pb-20 text-center space-y-8">
        
        {/* Pill Badge */}
        <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-indigo-50 border border-indigo-200/80 text-xs font-semibold text-indigo-700">
          <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
          <span>AI-powered CAD, from idea to production</span>
        </div>

        {/* Main Title */}
        <h1 className="text-5xl lg:text-6xl font-black text-slate-900 tracking-tight max-w-4xl mx-auto leading-[1.1]">
          Turn Ideas Into{' '}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600">
            Production-Ready CAD.
          </span>
        </h1>

        {/* Subtitle */}
        <p className="text-base md:text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed">
          Generate, edit, visualize, and export professional 2D and 3D CAD designs with AI — without leaving a real engineering workspace.
        </p>

        {/* Action Buttons */}
        <div className="flex items-center justify-center space-x-4 pt-2">
          <button
            onClick={() => setViewMode('auth')}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm px-6 py-3 rounded-xl shadow-lg shadow-blue-600/25 transition-all"
          >
            Get Started
          </button>
          <button
            onClick={() => setViewMode('dashboard')}
            className="bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 font-bold text-sm px-6 py-3 rounded-xl shadow-sm transition-all"
          >
            Explore Demo
          </button>
        </div>

      </section>

      {/* Divider */}
      <div className="max-w-6xl mx-auto border-t border-slate-200/80" />

      {/* 3. Section 2: Workspaces */}
      <section id="features" className="max-w-5xl mx-auto px-6 py-20 text-center space-y-12">
        
        <div className="space-y-2">
          <span className="text-xs font-mono font-bold tracking-widest text-indigo-600 uppercase">
            TWO WORKSPACES
          </span>
          <h2 className="text-3xl font-black text-slate-900 tracking-tight">
            One Workspace. Two CAD Modes.
          </h2>
          <p className="text-sm text-slate-600 max-w-xl mx-auto">
            Move fluidly between full 3D geometry and precise 2D technical drawings — the same AI assistant works across both.
          </p>
        </div>

        {/* 2 Feature Cards */}
        <div className="grid md:grid-cols-2 gap-8 text-left">
          
          {/* Card 1: 3D CAD */}
          <div className="bg-white border border-slate-200/80 p-8 rounded-3xl shadow-sm hover:shadow-md transition-shadow space-y-6">
            <div className="w-12 h-12 rounded-2xl bg-indigo-50 flex items-center justify-center text-indigo-600">
              <Hexagon className="w-6 h-6" />
            </div>

            <div className="space-y-2">
              <h3 className="text-xl font-bold text-slate-900">3D CAD</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Generate and edit detailed 3D models for engineering, prototyping, visualization, and manufacturing.
              </p>
            </div>

            <ul className="space-y-2 text-xs text-slate-600 pt-2 border-t border-slate-100">
              <li className="flex items-center space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-600" />
                <span>Text → 3D and Image → 3D</span>
              </li>
              <li className="flex items-center space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-600" />
                <span>AI-guided model editing</span>
              </li>
              <li className="flex items-center space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-600" />
                <span>Export STL, STEP, OBJ, GLB</span>
              </li>
            </ul>
          </div>

          {/* Card 2: 2D CAD */}
          <div className="bg-white border border-slate-200/80 p-8 rounded-3xl shadow-sm hover:shadow-md transition-shadow space-y-6">
            <div className="w-12 h-12 rounded-2xl bg-indigo-50 flex items-center justify-center text-indigo-600">
              <ArrowUpRight className="w-6 h-6" />
            </div>

            <div className="space-y-2">
              <h3 className="text-xl font-bold text-slate-900">2D CAD</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Create precise technical drawings, blueprints, and engineering layouts with correct dimensioning.
              </p>
            </div>

            <ul className="space-y-2 text-xs text-slate-600 pt-2 border-t border-slate-100">
              <li className="flex items-center space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-600" />
                <span>Auto front / top / side views</span>
              </li>
              <li className="flex items-center space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-600" />
                <span>Dimensions & annotations</span>
              </li>
              <li className="flex items-center space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-600" />
                <span>Export DXF, SVG, PDF</span>
              </li>
            </ul>
          </div>

        </div>

      </section>

      {/* 4. Section 3: Workflow */}
      <section className="bg-white border-y border-slate-200/80 py-20 px-6">
        <div className="max-w-5xl mx-auto space-y-12 text-center">
          
          <div className="space-y-2">
            <span className="text-xs font-mono font-bold tracking-widest text-indigo-600 uppercase">
              WORKFLOW
            </span>
            <h2 className="text-3xl font-black text-slate-900 tracking-tight">
              How CAD Studio Works
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 text-left">
            
            <div className="space-y-3">
              <span className="text-xs font-mono font-black text-indigo-600 block">01</span>
              <h4 className="text-sm font-bold text-slate-900">Describe your idea</h4>
              <p className="text-xs text-slate-600 leading-relaxed">
                Write a plain-language description or attach a reference image.
              </p>
            </div>

            <div className="space-y-3">
              <span className="text-xs font-mono font-black text-indigo-600 block">02</span>
              <h4 className="text-sm font-bold text-slate-900">AI generates the design</h4>
              <p className="text-xs text-slate-600 leading-relaxed">
                CAD Studio produces accurate, editable geometry in seconds.
              </p>
            </div>

            <div className="space-y-3">
              <span className="text-xs font-mono font-black text-indigo-600 block">03</span>
              <h4 className="text-sm font-bold text-slate-900">Inspect and refine</h4>
              <p className="text-xs text-slate-600 leading-relaxed">
                Adjust dimensions, materials, and geometry with AI or manual tools.
              </p>
            </div>

            <div className="space-y-3">
              <span className="text-xs font-mono font-black text-indigo-600 block">04</span>
              <h4 className="text-sm font-bold text-slate-900">Export your CAD file</h4>
              <p className="text-xs text-slate-600 leading-relaxed">
                Ship it as STL, STEP, OBJ, GLB, or DXF — ready for production.
              </p>
            </div>

          </div>

        </div>
      </section>

      {/* 5. Section 4: Capabilities */}
      <section className="max-w-5xl mx-auto px-6 py-20 space-y-12 text-center">
        
        <div className="space-y-2">
          <span className="text-xs font-mono font-bold tracking-widest text-indigo-600 uppercase">
            CAPABILITIES
          </span>
          <h2 className="text-3xl font-black text-slate-900 tracking-tight">
            Built for real engineering work
          </h2>
        </div>

        <div className="grid md:grid-cols-3 gap-6 text-left">
          
          <div className="bg-white border border-slate-200/80 p-6 rounded-2xl space-y-2 shadow-sm">
            <Sparkles className="w-5 h-5 text-indigo-600" />
            <h4 className="text-sm font-bold text-slate-900">AI CAD Assistant</h4>
            <p className="text-xs text-slate-600 leading-relaxed">
              Converse naturally to generate and modify geometry.
            </p>
          </div>

          <div className="bg-white border border-slate-200/80 p-6 rounded-2xl space-y-2 shadow-sm">
            <Hexagon className="w-5 h-5 text-indigo-600" />
            <h4 className="text-sm font-bold text-slate-900">3D Generation</h4>
            <p className="text-xs text-slate-600 leading-relaxed">
              Text and image driven model synthesis at production quality.
            </p>
          </div>

          <div className="bg-white border border-slate-200/80 p-6 rounded-2xl space-y-2 shadow-sm">
            <Layers className="w-5 h-5 text-indigo-600" />
            <h4 className="text-sm font-bold text-slate-900">2D Blueprint Generation</h4>
            <p className="text-xs text-slate-600 leading-relaxed">
              Standards-correct orthographic drawings, automatically.
            </p>
          </div>

          <div className="bg-white border border-slate-200/80 p-6 rounded-2xl space-y-2 shadow-sm">
            <Sliders className="w-5 h-5 text-indigo-600" />
            <h4 className="text-sm font-bold text-slate-900">Parametric Dimensions</h4>
            <p className="text-xs text-slate-600 leading-relaxed">
              Edit exact measurements and watch geometry update live.
            </p>
          </div>

          <div className="bg-white border border-slate-200/80 p-6 rounded-2xl space-y-2 shadow-sm">
            <Eye className="w-5 h-5 text-indigo-600" />
            <h4 className="text-sm font-bold text-slate-900">Model Viewer</h4>
            <p className="text-xs text-slate-600 leading-relaxed">
              A real-time viewport built for inspection, not just display.
            </p>
          </div>

          <div className="bg-white border border-slate-200/80 p-6 rounded-2xl space-y-2 shadow-sm">
            <Download className="w-5 h-5 text-indigo-600" />
            <h4 className="text-sm font-bold text-slate-900">Export Tools</h4>
            <p className="text-xs text-slate-600 leading-relaxed">
              One-click export across every major CAD and manufacturing format.
            </p>
          </div>

        </div>

      </section>

      {/* 6. Footer Call-to-action */}
      <section className="bg-white border-t border-slate-200/80 py-16 px-6 text-center space-y-6">
        <h3 className="text-3xl font-black text-slate-900 tracking-tight">
          Start designing in minutes.
        </h3>
        <button
          onClick={() => setViewMode('auth')}
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm px-8 py-3.5 rounded-xl shadow-lg shadow-blue-600/25 transition-all"
        >
          Start Designing
        </button>
      </section>

    </div>
  );
};
