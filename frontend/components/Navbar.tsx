import React from 'react'
import { FileText, Brain } from 'lucide-react'

const Navbar: React.FC = () => {
  return (
    <nav className="icici-navbar sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo and Brand */}
          <div className="flex items-center space-x-3">
            <div className="bg-primary p-2 rounded-lg">
              <FileText className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-secondary">
                BRS Merger
              </h1>
              <p className="text-xs text-muted-foreground flex items-center space-x-1">
                <Brain className="w-3 h-3" />
                <span>AI + RAG Powered</span>
              </p>
            </div>
          </div>

          {/* Navigation Links */}
          <div className="hidden md:flex items-center space-x-6">
            <a href="#" className="text-secondary hover:text-primary transition-colors font-medium">
              Home
            </a>
            <a href="#" className="text-muted-foreground hover:text-primary transition-colors">
              About
            </a>
            <a href="#" className="text-muted-foreground hover:text-primary transition-colors">
              Help
            </a>
          </div>

          {/* Mobile Menu Button */}
          <button className="md:hidden p-2 text-secondary">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
