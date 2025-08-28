// src/layouts/AppLayout.tsx
// Layout com Header "sticky" e Sidebar fixa. Use em todas as rotas protegidas.

import { PropsWithChildren } from "react";
import { SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { RuachLogo } from "@/components/ruach-logo";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import UserMenu from "@/components/account/UserMenu";
import { Bell, Search } from "lucide-react";

export default function AppLayout({ children }: PropsWithChildren) {
  return (
    <SidebarProvider>
      <div className="min-h-screen w-full bg-gradient-subtle">
        {/* Header fixo */}
        <header className="h-16 bg-background border-b border-border shadow-sm sticky top-0 z-40">
          <div className="flex items-center justify-between h-full px-4">
            {/* Branding */}
            <div className="flex items-center gap-4">
              <RuachLogo size="sm" />
            </div>

            {/* Busca (placeholder) */}
            <div className="hidden lg:flex items-center relative">
              <Search className="absolute left-3 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Buscar..." className="w-64 pl-10 input-ruach" />
            </div>

            {/* Ações à direita */}
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="icon" className="relative" title="Notificações">
                <Bell className="h-5 w-5" />
                <span className="absolute -top-1 -right-1 h-3 w-3 bg-destructive rounded-full text-[10px] text-destructive-foreground flex items-center justify-center">
                  3
                </span>
              </Button>
              <UserMenu />
            </div>
          </div>
        </header>

        {/* Corpo com Sidebar + conteúdo */}
        <div className="flex min-h-[calc(100vh-4rem)] w-full">
          <AppSidebar />
          <main className="flex-1 p-6 overflow-auto">{children}</main>
        </div>
      </div>
    </SidebarProvider>
  );
}
