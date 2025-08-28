import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RuachLogo } from "@/components/ruach-logo";
import { Eye, EyeOff, User, Lock } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { login, me } from "@/services/auth";

export default function Login() {
  const [showPassword, setShowPassword] = useState(false);
  const [identifier, setIdentifier] = useState(""); // email OU username
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const location = useLocation() as any;
  const next = location.state?.from?.pathname || "/dashboard";

  useEffect(() => {
    (async () => {
      try {
        // Se já está autenticado, redireciona
        const u = await me();
        if (u?.role === "bootstrap") {
          navigate("/setup", { replace: true });
        } else {
          navigate(next, { replace: true });
        }
      } catch {
        /* não autenticado */
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const resp = await login(identifier, password);

      // Papel bootstrap vai direto ao wizard de setup
      if (resp.user?.role === "bootstrap") {
        navigate("/setup", { replace: true });
        return;
      }

      if (resp.user.must_change_password) {
        navigate("/first-access", { replace: true }); // força troca de senha
      } else {
        navigate("/dashboard", { replace: true });
      }
    } catch (err: any) {
      console.error(err);
      setError(err?.message || "Falha no login");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-subtle flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center space-y-4">
          <RuachLogo size="lg" className="justify-center" />
          <div>
            <h1 className="text-2xl font-bold text-foreground">Bem-vindo de volta</h1>
            <p className="text-muted-foreground mt-2">Clareza para decidir melhor</p>
          </div>
        </div>

        <Card className="card-ruach border-2">
          <CardHeader className="space-y-1">
            <CardTitle className="text-xl text-center">Entrar</CardTitle>
            <CardDescription className="text-center">
              Use seu email ou usuário (bootstrap: use as credenciais iniciais)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="identifier" className="text-sm font-medium">Email ou usuário</Label>
                <div className="relative">
                  <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="identifier"
                    type="text"
                    placeholder="ex.: admin ou admin@empresa.com"
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    className="input-ruach pl-10"
                    required
                    autoFocus
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-sm font-medium">Senha</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Digite sua senha"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="input-ruach pl-10 pr-10"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-3 text-muted-foreground hover:text-foreground transition-colors"
                    aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {error && <div className="text-sm text-destructive">{error}</div>}

              <Button type="submit" className="w-full btn-ruach-primary h-11 text-base font-medium" disabled={isLoading}>
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Entrando...
                  </div>
                ) : ("Entrar")}
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="text-center text-sm text-muted-foreground">
          <p>Ao continuar, você concorda com nossos Termos de Uso e Política de Privacidade</p>
        </div>
      </div>
    </div>
  );
}
