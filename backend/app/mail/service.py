import os
from pathlib import Path
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.logging import logger
from jinja2 import Environment, FileSystemLoader, select_autoescape
import base64

TEMPLATE_DIR = Path(__file__).parent / "templates"

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(['html', 'xml'])
)

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM", "Athena Reports <noreply@athena.local>"),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.example.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "True").lower() == "true",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "False").lower() == "true",
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

def logo_to_base64(logo_path):
    """
    Converte um arquivo de imagem em base64 para uso inline no e-mail.
    Retorna uma string data-uri pronta para usar no src do <img>.
    """
    if not logo_path:
        return None
    try:
        logo_file = Path(logo_path)
        if not logo_file.exists():
            logger.warning(f"[Mail] Logo não encontrado: {logo_path}")
            return None
        with logo_file.open("rb") as f:
            encoded = base64.b64encode(f.read()).decode()
            mime = "image/png" if logo_file.suffix.lower() == ".png" else "image/jpeg"
            return f"data:{mime};base64,{encoded}"
    except Exception as e:
        logger.error(f"[Mail] Falha ao embutir logo no e-mail: {e}")
        return None

async def send_report_email(
    recipients: list,
    file_path: str = None,
    hostgroup_name: str = None,
    periodo: str = None,
    analyst: str = None,
    comments: str = None,
    logo_path: str = None,     # <-- Incluído!
    template_name: str = "report_email.html"
):
    """
    Envia o relatório em PDF para uma lista de destinatários, usando um template HTML.
    Agora suporta logo embutido!
    """
    try:
        # Gera logo_base64 se houver
        logo_base64 = logo_to_base64(logo_path)

        template = jinja_env.get_template(template_name)
        body_html = template.render(
            hostgroup_name=hostgroup_name,
            periodo=periodo,
            analyst=analyst,
            comments=comments,
            logo_base64=logo_base64  # <-- Disponível no template
        )

        subject = "Athena Reports - Relatório"
        if hostgroup_name:
            subject += f" {hostgroup_name}"
        if periodo:
            subject += f" ({periodo})"

        attachments = []
        if file_path:
            pdf_file = Path(file_path)
            if not pdf_file.exists():
                logger.error(f"[Mail] Arquivo PDF não encontrado: {file_path}")
                return
            attachments.append(str(pdf_file))

        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=body_html,
            attachments=attachments,
            subtype=MessageType.html
        )

        fm = FastMail(conf)
        await fm.send_message(message)
        logger.info(
            f"[Mail] Relatório enviado para: {', '.join(recipients)} | Arquivo: {file_path if file_path else '(sem anexo)'}"
        )

    except Exception as e:
        logger.error(f"[Mail] Erro ao enviar e-mail para {', '.join(recipients)}: {str(e)}")

def send_report_email_sync(recipients, file_path, hostgroup_name, periodo, analyst, comments, logo_path=None):
    """
    Envio síncrono de e-mail, usado pelo scheduler diretamente.
    """
    import asyncio
    from app.mail.service import send_report_email as async_email

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            async_email(
                recipients=recipients,
                file_path=file_path,
                hostgroup_name=hostgroup_name,
                periodo=periodo,
                analyst=analyst,
                comments=comments,
                logo_path=logo_path
            )
        )
        loop.close()
    except Exception as e:
        logger.error(f"[MAIL SYNC] Erro ao enviar e-mail: {str(e)}")
