import json
from sqlalchemy import or_, and_, func
from db.models import Question, UserOPEC
from core.competitions import get_active_competition_id
from core.legacy_question_audit import is_safe_for_active_study

class QuestionService:
    @staticmethod
    def get_questions_for_user(db, user_id, include_review=False):
        """
        Calcula las preguntas pertinentes para el usuario basándose en su OPEC activa.
        Utiliza un motor de keywords dinámico v48.1 Mikey.
        """
        user_opec = db.query(UserOPEC).filter_by(user_id=user_id, is_active=True).first()
        
        # El banco siempre se limita al concurso activo.
        competition_id = get_active_competition_id(db, user_id)
        query = db.query(Question)
        if competition_id is not None:
            query = query.filter(Question.competition_id == competition_id)

        all_candidates = query.all()
        if not include_review:
            all_candidates = [q for q in all_candidates if is_safe_for_active_study(q)]
        
        # Si no hay perfil, devolvemos todo (para Administradores o usuarios nuevos)
        if not user_opec:
            return all_candidates

        # Una competencia activa ya es el filtro más preciso. No excluir casos
        # curados solo porque su tema no repite literalmente el número OPEC.
        if competition_id is not None:
            return all_candidates

        # 1. Extracción de Keywords de la OPEC
        functions = user_opec.functions if isinstance(user_opec.functions, list) else []
        purpose = user_opec.purpose if user_opec.purpose else ""
        job_title = user_opec.job_title if user_opec.job_title else ""
        
        opec_text = (job_title + " " + purpose + " " + " ".join(functions)).lower()
        
        # 2. Detección de Naturaleza (Tributaria vs Aduanera)
        is_tributaria = any(w in opec_text for w in ['tributari', 'impuesto', 'renta', 'iva', 'cobro', 'recaudo'])
        is_aduanera = any(w in opec_text for w in ['aduan', 'arancel', 'import', 'export', 'tránsito', 'cabotaje', 'zona franca'])

        # 3. Aplicación de Filtros Maestro
        final_questions = []

        # [0] PRIORIDAD ABSOLUTA V50: Coincidencia Exacta de OPEC
        # Si existen preguntas "hechas a medida" para este código OPEC, ignoramos el resto.
        if user_opec.opec_number:
            strict_matches = [q for q in all_candidates if user_opec.opec_number in q.topic]
            # Si tenemos un banco decente (>10 preguntas) específico, usamos SOLO esto.
            if len(strict_matches) >= 5:
                # Opcional: Mezclar con comportamentales genéricas si se desea, 
                # pero por ahora devolvemos lo específico que es lo que pide el usuario.
                return strict_matches
        
        
        # [1] Heurística Keywords (Legacy / Fallback) - SI NO HAY MATCH EXACTO
        for q in all_candidates:
            q_text = (q.topic + " " + q.competency + " " + q.stem).lower()
            
            # A. Filtros Negativos Cruzados (Blindaje Cesar/Cualquier Usuario)
            # v6.4 Mikey: Los temas transversales (Integridad, Etica, Comportamental) NUNCA se filtran.
            is_transcendental = any(x in q_text for x in ['integridad', 'ética', 'etica', 'constitución', 'constitucion', 'comportamental', 'conductual'])
            
            if not is_transcendental:
                if is_tributaria and not is_aduanera:
                    # Si soy puramente tributario, prohibido temas de aduana (Cesar Rule)
                    forbidden = ['aduan', 'arancel', 'import', 'export', 'tráfico postal', 'cabotaje', 'zona franca']
                    if any(f in q_text for f in forbidden):
                        continue
                
                if is_aduanera and not is_tributaria:
                    # Si soy puramente aduanero, prohibido temas de recaudo tributario interno puro
                    forbidden = ['renta pbx', 'retención en la fuente', 'impuesto de consumo']
                    if any(f in q_text for f in forbidden):
                        continue

            # B. Validación de Formato GOA (Situacional + 3 Opciones)
            # Para cargos Profesionales (Nivel 1/2) somos más estrictos con el protocolo 2667
            is_behavioral = any(x in q.competency.lower() or x in q.topic.lower() for x in ['comportamental', 'conductual', 'integridad', 'valores', 'ética', 'etica'])
            
            if not is_behavioral:
                # Requerir formato situacional para preguntas técnicas (GOA 2667)
                if "SITUACIÓN" not in q.stem.upper():
                    continue
                
                # Requerir exactamente 3 opciones (Estándar CNSC 2024)
                try:
                    opts = q.options_json if isinstance(q.options_json, dict) else json.loads(q.options_json)
                    if len(opts) != 3:
                        continue
                except:
                    continue

            final_questions.append(q)
        
        return final_questions
