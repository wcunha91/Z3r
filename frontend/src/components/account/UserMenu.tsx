// src/components/account/UserMenu.tsx
// Dropdown com Perfil, Configurações, Trocar Senha e Sair.

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { getUser, clearAuth } from "@/lib/api";
import ChangePasswordDialog, { UserOut } from "@/components/account/ChangePasswordDialog";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ChevronDown, User, Settings, LogOut, Lock } from "lucide-react";

export default function UserMenu() {
  const navigate = useNavigate();
  const [dialogOpen, setDialogOpen] = useState(false);
  const user = getUser<UserOut>();

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="flex items-center gap-2 h-9 px-3">
            <Avatar className="h-7 w-7">
              <AvatarImage src="/api/placeholder/32/32" alt="Usuário" />
              <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                {(user?.name || user?.username || "RU").slice(0, 2).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div className="hidden md:flex flex-col items-start text-xs">
              <span className="font-medium">{user?.name || user?.username || "Ruach User"}</span>
              <span className="text-muted-foreground">{user?.role || "User"}</span>
            </div>
            <ChevronDown className="h-3 w-3 hidden md:block" />
          </Button>
        </DropdownMenuTrigger>

        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel>Minha Conta</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => navigate("/perfil")}>
            <User className="mr-2 h-4 w-4" />
            <span>Perfil</span>
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => navigate("/dashboard/configuracoes")}>
            <Settings className="mr-2 h-4 w-4" />
            <span>Configurações</span>
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setDialogOpen(true)}>
            <Lock className="mr-2 h-4 w-4" />
            <span>Trocar Senha</span>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            className="text-destructive focus:text-destructive"
            onClick={() => { clearAuth(); navigate("/login", { replace: true }); }}
          >
            <LogOut className="mr-2 h-4 w-4" />
            <span>Sair</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <ChangePasswordDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </>
  );
}
