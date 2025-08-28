//src/components/app-sidebar.tsx
import { useState } from "react";
import { 
  BarChart3, 
  Calendar, 
  FileText, 
  Clock, 
  Settings, 
  PlusCircle,
  Archive,
  TrendingUp
} from "lucide-react";
import { NavLink, useLocation } from "react-router-dom";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";

const reportItems = [
  { 
    title: "Gerar Relatório", 
    url: "/reports/new", 
    icon: PlusCircle,
    description: "Criar novo relatório"
  },
  { 
    title: "Relatórios", 
    url: "/reports", 
    icon: FileText,
    description: "Visualizar agendamentos"
  },
  { 
    title: "Relatórios Configurados", 
    url: "/configs", 
    icon: Archive,
    description: "Histórico de relatórios"
  }
];

const analyticsItems = [
  { 
    title: "Dashboard Analytics", 
    url: "/dashboard", 
    icon: BarChart3,
    description: "Visão geral dos dados"
  },
  { 
    title: "Métricas Principais", 
    url: "/dashboard", 
    icon: TrendingUp,
    description: "KPIs e indicadores"
  },
  { 
    title: "Arquivos", 
    url: "/dashboard", 
    icon: Archive,
    description: "Gerenciar arquivos"
  },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const location = useLocation();
  const currentPath = location.pathname;
  const isCollapsed = state === "collapsed";

  const isActive = (path: string) => currentPath === path;
  const isGroupExpanded = (items: typeof reportItems) => 
    items.some((item) => isActive(item.url));

  const getNavClass = (active: boolean) =>
    active 
      ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium shadow-sm" 
      : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground";

  return (
    <Sidebar
      className={`${isCollapsed ? "w-16" : "w-64"} transition-all duration-300`}
      collapsible="icon"
    >
      <SidebarContent className="bg-sidebar border-r border-sidebar-border">
        {/* Relatórios Section */}
        <SidebarGroup className="py-2">
          <SidebarGroupLabel className="text-xs font-semibold text-sidebar-foreground/70 uppercase tracking-wider px-3 py-2">
            {!isCollapsed && "Relatórios"}
          </SidebarGroupLabel>
          
          <SidebarGroupContent>
            <SidebarMenu className="space-y-1">
              {reportItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <NavLink
                      to={item.url}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${getNavClass(isActive(item.url))}`}
                       title={isCollapsed ? item.title : undefined}
                     >
                       <item.icon className="h-4 w-4 flex-shrink-0" />
                       {!isCollapsed && (
                        <div className="flex flex-col">
                          <span className="text-sm font-medium">{item.title}</span>
                          <span className="text-xs text-sidebar-foreground/60">{item.description}</span>
                        </div>
                      )}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Analytics Section */}
        <SidebarGroup className="py-2">
          <SidebarGroupLabel className="text-xs font-semibold text-sidebar-foreground/70 uppercase tracking-wider px-3 py-2">
            {!isCollapsed && "Analytics - Comming Soon"}
          </SidebarGroupLabel>
          
          <SidebarGroupContent>
            <SidebarMenu className="space-y-1">
              {analyticsItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <NavLink
                      to={item.url}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${getNavClass(isActive(item.url))}`}
                       title={isCollapsed ? item.title : undefined}
                     >
                       <item.icon className="h-4 w-4 flex-shrink-0" />
                       {!isCollapsed && (
                        <div className="flex flex-col">
                          <span className="text-sm font-medium">{item.title}</span>
                          <span className="text-xs text-sidebar-foreground/60">{item.description}</span>
                        </div>
                      )}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Settings Section */}
        <SidebarGroup className="mt-auto py-2">
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild>
                  <NavLink
                    to="/dashboard"
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${getNavClass(isActive("/dashboard/configuracoes"))}`}
                     title={isCollapsed ? "Configurações" : undefined}
                   >
                     <Settings className="h-4 w-4 flex-shrink-0" />
                     {!isCollapsed && (
                      <div className="flex flex-col">
                        <span className="text-sm font-medium">Configurações</span>
                        <span className="text-xs text-sidebar-foreground/60">Ajustes da conta</span>
                      </div>
                    )}
                  </NavLink>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}