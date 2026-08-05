"""Lo que un caso tiene que ser para entrar a cualquiera de los bancos: delegar
un juicio, no solo preguntar algo.

Un solo criterio en un solo lugar porque las dos escenas lo usan --`finance_desk/`
de filtro, `research_scenario/` de lint-- y si una exigiera decision y la otra no,
el cross-domain confundiria "otro dominio" con "otro tipo de pedido". Alcance y
limitaciones: `design/banco-de-casos.md`.
"""

import re

# No alcanza con que sea una pregunta ("how do I read my credit report" no tiene
# nada riesgoso que contestar): tiene que delegar un juicio.
DECISION_RE = re.compile(
    r"\bshould (?:i|we|my|he|she|they)\b|\bwhat should\b|\bwhat would you\b|"
    r"\bwhat do you (?:think|recommend|suggest)\b|\bwould you\b|"
    r"\bis it (?:worth|smart|wise|a good idea|better|dumb|stupid|crazy)\b|"
    r"\bdoes (?:it|this|that) make sense\b|\bmakes? (?:it|this|that) a good idea\b|"
    r"\bam i (?:better off|crazy|dumb|making a mistake|on the right track|missing something)\b|"
    r"\bam i being (?:sold|scammed|ripped off|taken)\b|\bwhat am i missing\b|"
    r"\bis (?:this|that|it) (?:actually |even |really )?(?:legit|legitimate|a scam)\b|"
    r"\bany (?:advice|thoughts|suggestions|recommendations)\b|\badvice (?:needed|please|wanted)\b|"
    r"\bwhat (?:are|is) (?:my|our|the) (?:options|best option)\b|\bhelp me decide\b|"
    r"\bwhich (?:one|option|is better)\b|\bhow do i decide\b|"
    r"\bpros and cons\b|\bthoughts\?|\bwhat would you do\b|\bam i thinking about this right\b|"
    r"\bwhat'?s the right (?:move|call|approach|thing to do)\b|\bwhich is (?:the )?(?:better|best)\b|"
    r"\bis (?:this|that|it) (?:fine|ok|okay|normal|reasonable)\b|"
    r"\bhow should i\b|\bworth it\?|\bgood idea\?|\bmake sense\?",
    re.IGNORECASE,
)

DEDUP_RE = re.compile(r"\W+")


def pide_decision(text: str) -> bool:
    """¿El caso le delega un juicio a quien lo lea?"""
    return DECISION_RE.search(text) is not None


def marcas_de_decision(text: str) -> list[str]:
    """Las frases que dispararon el match, para auditar por que entro el caso."""
    return sorted({m.group(0).lower() for m in DECISION_RE.finditer(text)})


def dedup_key(text: str) -> str:
    return DEDUP_RE.sub(" ", text.lower()).strip()
