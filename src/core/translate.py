"""Módulo de tradução com fallback automático.

Tenta:
  1. argos-translate (offline) — se instalado e pacotes de idioma baixados
  2. GoogleTranslator (online)  — fallback padrão
  3. Retorna texto original     — último fallback
"""

import logging

from src.configs import TRANSLATE_PREFERRED

log = logging.getLogger('vidra')


def translate(text: str, source: str = 'auto', target: str = 'pt') -> str:
    """Traduz texto usando o melhor motor disponível."""
    result = None
    errors = []

    # ── 1. argos-translate (offline) ──────────────────────────
    if TRANSLATE_PREFERRED in ('auto', 'offline'):
        try:
            result = _translate_argos(text, source, target)
        except Exception as exc:
            errors.append(f'offline: {exc}')
            log.debug('argos-translate indisponível, tentando online…')

    # ── 2. GoogleTranslator (online) ──────────────────────────
    if result is None and TRANSLATE_PREFERRED in ('auto', 'google'):
        try:
            result = _translate_google(text, source, target)
        except Exception as exc:
            errors.append(f'google: {exc}')
            log.debug('GoogleTranslator falhou: %s', exc)

    # ── 3. Fallback extremo ───────────────────────────────────
    if result is None:
        log.warning(
            'Tradução indisponível. Motivos: %s. Mantendo texto original.',
            '; '.join(errors)
        )
        return text

    return result


# ── engines ───────────────────────────────────────────────

def _translate_argos(text: str, source: str, target: str) -> str | None:
    """Tradução offline via argos-translate."""
    import argostranslate.package
    import argostranslate.translate

    # Instala pacote se necessário (primeira execução)
    argostranslate.package.update_package_index()
    available = argostranslate.package.get_available_packages()
    package = next(
        (p for p in available if p.from_code == source and p.to_code == target),
        None
    )
    # Se 'auto', tenta achar pacote que combine
    if not package and source == 'auto':
        package = next(
            (p for p in available if p.to_code == target),
            None
        )

    if package and not package.is_installed:
        log.info('  Instalando pacote de tradução %s→%s…', package.from_code, target)
        package.install()

    result = argostranslate.translate.translation(text, source, target)
    return result if result and result != text else None


def _translate_google(text: str, source: str, target: str) -> str:
    """Tradução online via GoogleTranslator."""
    from deep_translator import GoogleTranslator
    return GoogleTranslator(source=source, target=target).translate(text)
