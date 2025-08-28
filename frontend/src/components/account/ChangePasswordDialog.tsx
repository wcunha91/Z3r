// src/components/account/ChangePasswordDialog.tsx
// Modal reutilizável para troca de senha, usando /auth/change-password.

import { useState } from "react";
import { API_BASE, authHeaders, setUser } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle,
} from "@/components/ui/dialog";

export type UserOut = {
  email: string;
  username: string;
  name: string;
  role: string;
  must_change_password: boolean;
};

type Props = {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onSuccess?: (user: UserOut) => void;
};

export default function ChangePasswordDialog({ open, onOpenChange, onSuccess }: Props) {
  const [pwCurrent, setPwCurrent] = useState("");
  const [pwNew, setPwNew] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  const submit = async () => {
    setErr(null); setOk(null);
    if (!pwCurrent || !pwNew) { setErr("Preencha os dois campos."); return; }
    if (pwNew.length < 8) { setErr("A nova senha deve ter ao menos 8 caracteres."); return; }
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/auth/change-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ current_password: pwCurrent, new_password: pwNew }),
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Falha ao trocar senha (${res.status}): ${txt}`);
      }
      const user = (await res.json()) as UserOut;
      setUser(user);                 // atualiza localStorage
      onSuccess?.(user);
      setOk("Senha alterada com sucesso!");
      setPwCurrent(""); setPwNew("");
      setTimeout(() => onOpenChange(false), 600);
    } catch (e: any) {
      setErr(e?.message || "Erro ao trocar senha.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Trocar Senha</DialogTitle>
          <DialogDescription>Use ao menos 8 caracteres. Você permanecerá conectado.</DialogDescription>
        </DialogHeader>

        <div className="grid gap-3 py-2">
          <div className="grid gap-1">
            <label className="text-sm font-medium" htmlFor="pwCurrent">Senha atual</label>
            <Input id="pwCurrent" type="password" value={pwCurrent} onChange={(e) => setPwCurrent(e.target.value)} />
          </div>
          <div className="grid gap-1">
            <label className="text-sm font-medium" htmlFor="pwNew">Nova senha</label>
            <Input id="pwNew" type="password" value={pwNew} onChange={(e) => setPwNew(e.target.value)} />
          </div>
          {err && <div className="text-sm text-destructive">{err}</div>}
          {ok && <div className="text-sm text-green-600">{ok}</div>}
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>Cancelar</Button>
          <Button className="btn-ruach-primary" onClick={submit} disabled={loading}>
            {loading ? "Salvando..." : "Salvar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
