"""
Generador de afirmaciones éticas con IA para el módulo de Ética e Integridad.
Genera afirmaciones adaptativas basadas en las debilidades del usuario.
"""

import json
from typing import List, Dict
from core.generators.llm import LLMGenerator


def generate_ethics_statements(
    llm_generator: LLMGenerator,
    categoria: str,
    count: int = 10,
    weak_categories: List[str] = None
) -> List[Dict[str, str]]:
    """
    Genera afirmaciones éticas usando IA.
    
    Args:
        llm_generator: Instancia del generador LLM
        categoria: Categoría ética (Conflicto de Intereses, etc.)
        count: Número de afirmaciones a generar
        weak_categories: Categorías donde el usuario ha mostrado debilidad
        
    Returns:
        Lista de diccionarios con 'categoria' y 'afirmacion'
    """
    
    # Contexto del Código de Ética DIAN
    ethics_context = """
    CÓDIGO DE ÉTICA DIAN - VALORES INSTITUCIONALES:
    
    1. INTEGRIDAD: Actuar con rectitud, honradez y coherencia. Rechazar dádivas, declarar conflictos de interés, no usar información privilegiada.
    
    2. TRANSPARENCIA: Hacer visible la gestión pública. Documentar actuaciones, facilitar acceso a información, comunicar decisiones claramente.
    
    3. RESPONSABILIDAD: Cumplir obligaciones y asumir consecuencias. Responder oportunamente, proteger recursos públicos.
    
    4. RESPETO: Reconocer la dignidad de todas las personas. Tratar con cortesía, no discriminar, mantener ambiente laboral sano.
    
    5. IMPARCIALIDAD: Decisiones basadas exclusivamente en criterios técnicos y legales, sin favoritismos.
    
    6. CONFLICTO DE INTERESES: Nunca participar en decisiones que involucren familiares o amigos cercanos.
    """
    
    # Énfasis en categorías débiles
    emphasis = ""
    if weak_categories and categoria in weak_categories:
        emphasis = f"\n\n⚠️ ÉNFASIS: El usuario ha mostrado debilidad en '{categoria}'. Genera afirmaciones que ayuden a reforzar este aspecto específico con casos más sutiles y complejos."
    
    # Prompt para el LLM
    prompt = f"""
{ethics_context}

TAREA: Genera {count} afirmaciones para evaluar la comprensión del Código de Ética DIAN usando Escala Likert.

CATEGORÍA OBJETIVO: {categoria}

INSTRUCCIONES:
1. Cada afirmación debe ser una situación ética ambigua o dilema moral relacionado con {categoria}
2. Las afirmaciones deben ser realistas y aplicables al contexto de un funcionario de la DIAN
3. Algunas afirmaciones deben ser claramente correctas según el código de ética
4. Otras deben ser claramente incorrectas (violaciones éticas)
5. Algunas deben ser sutiles o en zona gris para evaluar comprensión profunda
6. Usa lenguaje profesional y formal
7. Evita afirmaciones obvias o triviales

{emphasis}

FORMATO DE SALIDA (JSON):
{{
  "afirmaciones": [
    "Afirmación 1 aquí",
    "Afirmación 2 aquí",
    ...
  ]
}}

EJEMPLOS DE BUENAS AFIRMACIONES:
- "Es aceptable recibir un regalo de bajo valor de un contribuyente agradecido después de resolver favorablemente su caso"
- "Un funcionario puede usar su conocimiento del sistema tributario para asesorar a familiares sobre cómo reducir legalmente sus impuestos"
- "La información sobre fiscalizaciones en curso puede compartirse con colegas de otras áreas si es para mejorar la coordinación institucional"

Genera ahora {count} afirmaciones nuevas y variadas para la categoría {categoria}.
"""
    
    try:
        # Llamar al LLM
        if llm_generator.provider == "gemini" and llm_generator.gemini_client:
            response = llm_generator.gemini_client.models.generate_content(
                model=llm_generator.model_name or "gemini-2.0-flash-exp",
                contents=prompt
            )
            raw_text = response.text
        elif llm_generator.openai_client:
            response = llm_generator.openai_client.chat.completions.create(
                model=llm_generator.model_name or "gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8
            )
            raw_text = response.choices[0].message.content
        else:
            raise Exception("No LLM client available")
        
        # Parsear JSON
        # Buscar el JSON en la respuesta
        import re
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            afirmaciones = data.get("afirmaciones", [])
            
            # Formatear resultado
            result = []
            for afirmacion in afirmaciones[:count]:
                result.append({
                    "categoria": categoria,
                    "afirmacion": afirmacion
                })
            
            return result
        else:
            raise Exception("No JSON found in response")
            
    except Exception as e:
        print(f"Error generating ethics statements: {e}")
        return []


def evaluate_ethics_response(
    categoria: str,
    afirmacion: str,
    respuesta_usuario: int
) -> tuple[bool, int, str]:
    """
    Evalúa si la respuesta del usuario es correcta según el Código de Ética DIAN.
    
    Args:
        categoria: Categoría ética
        afirmacion: Texto de la afirmación
        respuesta_usuario: Respuesta del usuario (1-5)
        
    Returns:
        (es_correcta, respuesta_esperada, explicacion)
    """
    
    # Palabras clave que indican violación ética (respuesta esperada: 1-2)
    violation_keywords = [
        "aceptable recibir", "puede usar", "es válido", "está permitido",
        "no hay problema", "se puede compartir", "ayudar a", "asesorar a",
        "tramitar", "gestionar para", "facilitar", "agilizar para"
    ]
    
    # Palabras clave que indican conducta ética correcta (respuesta esperada: 4-5)
    ethical_keywords = [
        "debe declarar", "siempre rechazar", "nunca aceptar", "abstenerse",
        "reportar inmediatamente", "denunciar", "documentar", "transparente",
        "imparcial", "objetivo", "técnico", "legal"
    ]
    
    afirmacion_lower = afirmacion.lower()
    
    # Determinar respuesta esperada
    is_violation = any(keyword in afirmacion_lower for keyword in violation_keywords)
    is_ethical = any(keyword in afirmacion_lower for keyword in ethical_keywords)
    
    if is_violation:
        # Afirmación describe una violación ética -> respuesta esperada: 1-2 (desacuerdo)
        respuesta_esperada = 1
        es_correcta = respuesta_usuario <= 2
        explicacion = "Esta afirmación describe una violación al Código de Ética. La respuesta correcta es estar en desacuerdo (1-2)."
    elif is_ethical:
        # Afirmación describe conducta ética correcta -> respuesta esperada: 4-5 (acuerdo)
        respuesta_esperada = 5
        es_correcta = respuesta_usuario >= 4
        explicacion = "Esta afirmación describe una conducta ética correcta. La respuesta correcta es estar de acuerdo (4-5)."
    else:
        # Caso ambiguo - evaluación basada en categoría
        if "conflicto" in categoria.lower() or "información" in categoria.lower():
            # Categorías sensibles: generalmente requieren desacuerdo con situaciones ambiguas
            respuesta_esperada = 2
            es_correcta = respuesta_usuario <= 3
            explicacion = "En casos de conflicto de intereses o información privilegiada, la postura más segura es el rechazo o abstención."
        else:
            # Neutral - aceptamos respuestas moderadas
            respuesta_esperada = 3
            es_correcta = 2 <= respuesta_usuario <= 4
            explicacion = "Esta afirmación requiere análisis contextual. Las respuestas moderadas son aceptables."
    
    return es_correcta, respuesta_esperada, explicacion


def detect_weak_categories(user_id: int, db_session) -> List[str]:
    """
    Detecta las categorías éticas donde el usuario ha mostrado debilidad.
    
    Args:
        user_id: ID del usuario
        db_session: Sesión de base de datos
        
    Returns:
        Lista de categorías donde el usuario necesita refuerzo
    """
    from db.models import EthicsAttempt
    from sqlalchemy import func, case
    
    try:
        # Obtener estadísticas por categoría
        stats = db_session.query(
            EthicsAttempt.categoria,
            func.count(EthicsAttempt.id).label('total'),
            func.sum(case((EthicsAttempt.es_correcta == True, 1), else_=0)).label('correctas')
        ).filter(
            EthicsAttempt.user_id == user_id
        ).group_by(
            EthicsAttempt.categoria
        ).all()
        
        weak_categories = []
        for stat in stats:
            if stat.total >= 3:  # Mínimo 3 intentos para considerar
                accuracy = (stat.correctas or 0) / stat.total
                if accuracy < 0.6:  # Menos del 60% de aciertos
                    weak_categories.append(stat.categoria)
        
        return weak_categories
    except Exception as e:
        print(f"Error detecting weak categories: {e}")
        return []
