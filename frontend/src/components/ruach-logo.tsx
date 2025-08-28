import { cn } from "@/lib/utils";

/**
 * RuachLogo
 * - Mantém a mesma assinatura (size, className, showText)
 * - Se encontrar imagens no /public (ou via env), usa elas
 *   - showText=true  => usa LOGO completo (com tipografia da marca)
 *   - showText=false => usa apenas o ÍCONE
 * - Se não houver imagens, renderiza o SVG antigo (fallback)
 */
interface RuachLogoProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  showText?: boolean;
}

const LOGO_URL =
  import.meta.env.VITE_BRAND_LOGO_URL ?? "/brand/z3-logo.svg";
const ICON_URL =
  import.meta.env.VITE_BRAND_ICON_URL ?? "/brand/z3-icon.svg";

export function RuachLogo({ size = "md", className, showText = true }: RuachLogoProps) {
  // Altura padrão por tamanho (mantém proporção da imagem)
  const sizeClasses = {
    sm: showText ? "h-12" : "h-10 w-10",
    md: showText ? "h-28" : "h-14 w-14",
    lg: showText ? "h-40" : "h-20 w-20",
  };


  // --- tenta usar imagens do brand ---
  const imgSrc = showText ? LOGO_URL : ICON_URL;
  const isBrandAsset = typeof imgSrc === "string" && imgSrc.startsWith("/");

  return (
    <div className={cn("flex items-center gap-2", className)}>
      {/* Caso exista imagem no /public (ou via env), usamos ela */}
      {isBrandAsset ? (
        <img
          src={imgSrc}
          alt={showText ? "Logo" : "Logo - Ícone"}
          className={cn("select-none object-contain", sizeClasses[size])}
          draggable={false}
        />
      ) : (
        // --- Fallback: SVG antigo (nada no /public) ---
        <div className={cn("relative flex items-center justify-center", sizeClasses[size])}>
          <svg
            viewBox="0 0 32 32"
            className="w-full h-full"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-label="Logo"
          >
            <defs>
              <linearGradient id="ruachGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style={{ stopColor: "hsl(var(--ruach-teal-deep))" }} />
                <stop offset="100%" style={{ stopColor: "hsl(var(--ruach-teal-light))" }} />
              </linearGradient>
            </defs>
            <path
              d="M16 4 C22 4 28 10 28 16 C28 20 25 23 21 23 C19 23 17 21 17 19 C17 18 18 17 19 17 C20 17 21 18 21 19"
              stroke="url(#ruachGradient)"
              strokeWidth="2"
              fill="none"
              strokeLinecap="round"
            />
            <circle cx="8" cy="8" r="1.5" fill="hsl(var(--ruach-gold))" />
            <circle cx="24" cy="8" r="1.5" fill="hsl(var(--ruach-gold))" />
            <circle cx="8" cy="24" r="1.5" fill="hsl(var(--ruach-gold))" />
            <path
              d="M9.5 8.5 L14 13 M22.5 8.5 L18 13 M9.5 23.5 L14 19"
              stroke="hsl(var(--ruach-teal-light))"
              strokeWidth="1"
              strokeOpacity="0.6"
            />
          </svg>
        </div>
      )}

      {/* Mantemos o texto opcional da versão antiga apenas no fallback (quando não há logo completo).
         Se você quiser NUNCA renderizar texto porque seu logo já tem tipografia, pode remover
         o bloco abaixo por completo. */}
      {!isBrandAsset && showText && (
        <span className={cn("font-bold tracking-tight", { sm: "text-lg", md: "text-xl", lg: "text-3xl" }[size])}>
          <span className="bg-gradient-ruach bg-clip-text text-transparent">Z3 Report</span>
        </span>
      )}
    </div>
  );
}
