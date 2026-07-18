import os
import sys
import uuid
import datetime

# Asegurar que la raíz del proyecto esté en el PYTHONPATH para importar db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.session import SessionLocal, engine
from db.models import CaseStudy, Question
from core.dedupe import compute_hash

def insert_custom_questions():
    print("🚀 Iniciando la inserción de 50 preguntas situacionales de alta complejidad para OPEC 236769...")
    
    # 5 Casos de Estudio de la DIAN
    CASES_DATA = [
        {
            "id": "case-01-renta-juridicas",
            "title": "Caso 1: Fiscalización de Inexactitudes y Omisiones en Impuesto sobre la Renta (Personas Jurídicas)",
            "text": "La sociedad 'Inversiones Caribe S.A.S.', dedicada al comercio al por mayor de bienes de consumo, es objeto de una auditoría por parte de la Subdirección de Fiscalización Tributaria de la DIAN por el año gravable 2024. Tras cruzar la información exógena reportada por sus clientes y entidades financieras, el auditor detecta una discrepancia de COP 1.200 millones en ingresos brutos no declarados. Adicionalmente, el contribuyente incluyó como deducciones pasivos inexistentes con proveedores ficticios de insumos por valor de COP 450 millones, soportados en facturas apócrifas expedidas por empresas que no cuentan con activos reales ni capacidad operativa. Ante este panorama de subdeclaración e inexactitud material, la DIAN inicia el proceso de determinación de tributos e imposición de sanciones.",
            "difficulty": 3,
            "topic": "OPEC 236769 - Fiscalización de Impuesto sobre la Renta Jurídicas",
            "questions": [
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Plazo Requerimiento Especial",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Determinación de Impuestos",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: Tras finalizar el análisis preliminar de las inconsistencias en la declaración de renta de 'Inversiones Caribe S.A.S.', el auditor de la DIAN prepara el Requerimiento Especial. PREGUNTA: Conforme al Artículo 707 del Estatuto Tributario, ¿cuál es el plazo legal que tiene el contribuyente para dar respuesta formal por escrito a este Requerimiento Especial?",
                    "options": {
                        "A": "Tres (3) meses contados a partir de la fecha de notificación del requerimiento especial.",
                        "B": "Un (1) mes contado a partir de la fecha de notificación del requerimiento especial.",
                        "C": "Dos (2) meses contados a partir de la fecha de notificación del requerimiento especial."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 707 del Estatuto Tributario colombiano establece expresamente que el contribuyente o su apoderado disponen de un término de tres (3) meses para formular sus objeciones y responder por escrito al Requerimiento Especial."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Régimen Sancionatorio",
                    "topic": "OPEC 236769 - Sanción por Inexactitud General",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Sanciones Tributarias",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: El auditor de la DIAN propone sanción por inexactitud debido a los pasivos inexistentes con proveedores ficticios. PREGUNTA: De acuerdo con la Ley 2277 de 2022 y el Artículo 648 del Estatuto Tributario, ¿cuál es la tarifa de la sanción por inexactitud aplicable por omitir ingresos o incluir pasivos inexistentes?",
                    "options": {
                        "A": "El 100% de la diferencia entre el saldo a pagar o saldo a favor determinado oficialmente y el declarado.",
                        "B": "El 160% de la diferencia entre el saldo determinado oficialmente y el valor liquidado en la declaración.",
                        "C": "El 20% del total de las deducciones improcedentes o ingresos omitidos."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 648 del Estatuto Tributario modificado por reformas recientes indica que la sanción general por inexactitud equivale al cien por ciento (100%) de la diferencia entre el saldo a pagar o saldo a favor, según el caso, determinado en la liquidación oficial y el declarado por el contribuyente. (Se redujo del histórico 160% al 100%)."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Notificación Electrónica de Actos",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Actos Administrativos",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: La DIAN envía el Requerimiento Especial a través de la bandeja electrónica del portal MUISCA. PREGUNTA: Según el Artículo 566-1 del Estatuto Tributario, ¿cuándo se entiende legalmente surtida la notificación enviada por medios electrónicos?",
                    "options": {
                        "A": "El día en que el contribuyente abra o ingrese efectivamente a leer la comunicación electrónica.",
                        "B": "En la fecha en que el acto administrativo es entregado en la bandeja del buzón electrónico del contribuyente.",
                        "C": "A los cinco (5) días hábiles siguientes a la fecha en que el acto sea depositado en el buzón electrónico."
                    },
                    "correct_key": "C",
                    "rationale": "El Artículo 566-1 del E.T. determina que la notificación electrónica se entenderá surtida para todos los efectos legales a los cinco (5) días hábiles siguientes a la fecha en que el acto administrativo sea depositado en el buzón de la cuenta del contribuyente."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Ampliación del Requerimiento",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Determinación de Impuestos",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: Tras recibir la respuesta del contribuyente, el auditor encuentra nuevos indicios de fraude que requieren aclaración. PREGUNTA: De acuerdo con el Artículo 708 del E.T., ¿en qué término y cuántas veces puede la DIAN proferir una ampliación al Requerimiento Especial?",
                    "options": {
                        "A": "Por una sola vez, dentro de los tres (3) meses siguientes al vencimiento del término para responder el requerimiento inicial.",
                        "B": "Hasta dos veces, dentro de los seis (6) meses siguientes al vencimiento del término original de respuesta.",
                        "C": "Por una sola vez, dentro de los dos (2) meses siguientes a la radicación de la respuesta del contribuyente."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 708 del Estatuto Tributario estipula que el funcionario que conozca del expediente podrá, por una sola vez, proferir ampliación al Requerimiento Especial, dentro de los tres (3) meses siguientes a la fecha de vencimiento del término para responder el Requerimiento Especial."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Corrección Provocada por Requerimiento",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Sanciones Tributarias",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: Al recibir el Requerimiento Especial, la sociedad decide aceptar parcialmente los ingresos omitidos para evitar el proceso legal extenso. PREGUNTA: De conformidad con el Artículo 709 del Estatuto Tributario, si el contribuyente corrige su declaración con ocasión del Requerimiento Especial, ¿a qué beneficio sancionatorio tiene derecho?",
                    "options": {
                        "A": "Reducción de la sanción por inexactitud al 50% de la inicialmente propuesta por la administración.",
                        "B": "Reducción de la sanción por inexactitud a la cuarta parte (25%) de la inicialmente formulada.",
                        "C": "Condonación total de los intereses de mora devengados hasta la fecha de corrección."
                    },
                    "correct_key": "B",
                    "rationale": "El Artículo 709 del Estatuto Tributario señala que si el contribuyente acepta total o parcialmente las glosas planteadas en el Requerimiento Especial y corrige su declaración, la sanción por inexactitud se reducirá a la cuarta parte (25%) de la inicialmente propuesta en relación con los hechos aceptados."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Liquidación de Aforo",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Determinación de Impuestos",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: Si la sociedad hubiese sido omisa absoluta en declarar y no respondiera a los emplazamientos de la DIAN. PREGUNTA: Según el Artículo 717 del Estatuto Tributario, ¿cuál es el acto administrativo definitivo con el cual la DIAN determina oficialmente la obligación ante la omisión absoluta?",
                    "options": {
                        "A": "Liquidación Oficial de Revisión.",
                        "B": "Liquidación Oficial de Aforo.",
                        "C": "Resolución Sanción por no Declarar."
                    },
                    "correct_key": "B",
                    "rationale": "El Artículo 717 establece que cuando los contribuyentes omitan la presentación de las declaraciones tributarias, la DIAN podrá determinar oficialmente la obligación del impuesto mediante la proferición de una Liquidación Oficial de Aforo, previo emplazamiento para declarar."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Emplazamiento para Declarar",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Obligaciones Formales",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: La DIAN detecta que la sociedad no declaró renta y procede a notificar un Emplazamiento para Declarar. PREGUNTA: De acuerdo con el Artículo 715 del Estatuto Tributario, ¿de cuánto tiempo dispone el contribuyente emplazado para presentar su declaración y evitar la Liquidación de Aforo?",
                    "options": {
                        "A": "Quince (15) días calendario siguientes a la fecha de notificación.",
                        "B": "Un (1) mes calendario contado a partir de la notificación del emplazamiento.",
                        "C": "Treinta (30) días hábiles siguientes a la fecha de notificación."
                    },
                    "correct_key": "B",
                    "rationale": "El Artículo 715 del Estatuto Tributario consagra que, previo a la Liquidación de Aforo, quienes incumplan con la obligación de declarar serán emplazados por la administración para que lo hagan dentro del término perentorio de un (1) mes."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Régimen Sancionatorio",
                    "topic": "OPEC 236769 - Sanción Extemporaneidad con Emplazamiento",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Sanciones Tributarias",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: La sociedad presenta la declaración omitida a raíz del Emplazamiento para Declarar, pero antes de que le notifiquen la sanción oficial. PREGUNTA: Conforme al Artículo 642 del Estatuto Tributario, ¿a cuánto equivale la sanción por extemporaneidad cuando se liquida con posterioridad al emplazamiento?",
                    "options": {
                        "A": "Al 10% del impuesto a cargo por cada mes o fracción de mes de retardo, sin superar el 200% del impuesto.",
                        "B": "Al 5% del impuesto a cargo por cada mes o fracción de mes de retardo, con un tope del 100% del impuesto.",
                        "C": "Al 20% de los ingresos brutos del contribuyente por el período no declarado."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 642 del Estatuto Tributario establece que si la declaración extemporánea se presenta con posterioridad al emplazamiento para declarar, la sanción será del diez por ciento (10%) del impuesto a cargo por cada mes o fracción de mes calendario de retardo, sin exceder el doscientos por ciento (200%) del impuesto a cargo."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Requisitos de Deducciones",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Sustanciación e Impuestos",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: Al auditar las compras de 'Inversiones Caribe S.A.S.', el funcionario nota que varias compras no están facturadas electrónicamente sino con documentos POS obsoletos. PREGUNTA: De acuerdo con el Artículo 771-2 del Estatuto Tributario, ¿cuál es el requisito indispensable para la procedencia de costos y deducciones en el impuesto sobre la renta?",
                    "options": {
                        "A": "Estar respaldados únicamente en facturas de venta o documentos equivalentes con el lleno de los requisitos legales vigentes.",
                        "B": "Haber realizado el pago de la obligación en efectivo directamente al proveedor en su domicilio comercial.",
                        "C": "Contar con el registro del contrato firmado ante una notaría pública del territorio nacional."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 771-2 del E.T. estatuye de manera explícita que para la procedencia de costos y deducciones en el impuesto sobre la renta, así como de los impuestos descontables en el IVA, se requiere de facturas de venta, documentos equivalentes o documentos soporte en adquisiciones efectuadas a sujetos no obligados a expedir factura, cumpliendo los requisitos legales."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Término de Firmeza General",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Determinación de Impuestos",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: La sociedad presenta su declaración de renta del año 2024 de forma oportuna y correcta sin saldos a favor ni pérdidas fiscales. PREGUNTA: Conforme a la regla general del Artículo 714 del Estatuto Tributario, ¿en cuánto tiempo queda en firme la declaración tributaria si no se notifica requerimiento especial?",
                    "options": {
                        "A": "En tres (3) años contados a partir del vencimiento del plazo para declarar o de la fecha de su presentación extemporánea.",
                        "B": "En cinco (5) años contados desde la fecha de presentación oportuna de la declaración tributaria.",
                        "C": "En dos (2) años contados a partir de la fecha de presentación de la declaración."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 714 del Estatuto Tributario, modificado por la Ley 2010 de 2019, fija en tres (3) años el término general de firmeza de las declaraciones tributarias, contados desde el vencimiento del término para declarar (si se presentó a tiempo) o desde la presentación (si fue extemporánea)."
                }
            ]
        },
        {
            "id": "case-02-evasion-lavado",
            "title": "Caso 2: Detección de Operaciones Ficticias, Facturación Apócrifa y Lavado de Activos",
            "text": "La Unidad de Investigación e Inteligencia Tributaria de la DIAN realiza un operativo contra una red criminal que provee facturas electrónicas apócrifas por falsos servicios de asesoría e intangibles. Al rastrear las transacciones, se observa que la firma 'Asesorías Alfa S.A.S.' facturó más de COP 5.000 millones a diversas empresas reales del sector de la construcción, recibiendo pagos bancarizados que de inmediato eran retirados en efectivo en sucursales bancarias de frontera o transferidos a cuentas en jurisdicciones de baja imposición tributaria (paraísos fiscales). El auditor de la DIAN debe declarar la inexistencia de estas operaciones, anular los costos e IVA descontables aplicados por los compradores, e informar a los entes competentes ante la sospecha inminente de lavado de activos y fraude aduanero.",
            "difficulty": 3,
            "topic": "OPEC 236769 - Fiscalización de Facturas Ficticias y Lavado",
            "questions": [
                {
                    "track": "FUNCIONAL",
                    "competency": "Detección de Evasión",
                    "topic": "OPEC 236769 - Declaratoria de Proveedor Ficticio",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Evasión y Elusión",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: Tras comprobar la total ausencia de personal e infraestructura en 'Asesorías Alfa S.A.S.', el funcionario proyecta el acto administrativo correspondiente. PREGUNTA: De conformidad con el Artículo 671 del Estatuto Tributario, ¿con qué declaración formal califica la DIAN a las personas naturales o jurídicas que simulan operaciones a través de facturación electrónica sin soporte real?",
                    "options": {
                        "A": "Declaratoria de Contribuyentes Inactivos y Sospechosos.",
                        "B": "Declaratoria de Proveedores Ficticios o Insolventes.",
                        "C": "Declaratoria de Entidades No Operativas e Inexistentes."
                    },
                    "correct_key": "B",
                    "rationale": "El Artículo 671 del Estatuto Tributario faculta a la DIAN para declarar como Proveedores Ficticios a aquellas personas o entidades que facturen operaciones simuladas o inexistentes, con la consecuencia directa de que no se admitirán las compras ni los impuestos descontables originados en dichas facturas."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Detección de Evasión",
                    "topic": "OPEC 236769 - Efectos Proveedor Ficticio",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Evasión y Elusión",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: La DIAN publica la resolución de proveedor ficticio contra 'Asesorías Alfa S.A.S.'. PREGUNTA: De acuerdo con el mismo Artículo 671 del E.T., ¿a partir de qué momento no son deducibles los costos y gastos amparados en facturas del proveedor ficticio por parte de sus clientes?",
                    "options": {
                        "A": "A partir de la fecha de publicación de la respectiva resolución en el Diario Oficial o página web de la DIAN.",
                        "B": "Con efecto retroactivo al primer día del año gravable en que se iniciaron las compras del proveedor simulado.",
                        "C": "A partir del vencimiento del término para interponer recursos de apelación en la vía gubernativa."
                    },
                    "correct_key": "A",
                    "rationale": "La norma indica expresamente que las compras, costos o gastos que se realicen a partir de la publicación de la declaratoria de proveedores ficticios en la página web de la DIAN o diario oficial, no serán deducibles en el impuesto sobre la renta ni darán derecho a impuestos descontables en el IVA."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Detección de Evasión",
                    "topic": "OPEC 236769 - Bancarización y Medios de Pago",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Fiscalización Aduanera",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: Para disimular el fraude, los compradores pagaron las facturas a 'Asesorías Alfa S.A.S.' mediante transferencias, pero de inmediato los fondos se retiraron en efectivo. PREGUNTA: De acuerdo con el Artículo 771-5 del E.T. (Bancarización), ¿cuáles son los medios de pago obligatorios reconocidos para la aceptación de costos, deducciones e IVA descontables?",
                    "options": {
                        "A": "Depósitos en cuentas bancarias, giros o transferencias bancarias, cheques con restricción de páguese al primer beneficiario y tarjetas de crédito o débito.",
                        "B": "Cualquier método acordado por las partes, siempre y cuando se anexe recibo de caja firmado con huella dactilar.",
                        "C": "Únicamente consignaciones en efectivo realizadas directamente en la ventanilla del banco receptor."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 771-5 del E.T. impone severos límites a los pagos en efectivo para efectos tributarios. Exige que los pagos para aceptación fiscal se realicen por canales financieros: depósitos bancarios, giros/transferencias, cheques cruzados o tarjetas bancarias."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Investigación Tributaria",
                    "topic": "OPEC 236769 - Reporte de Operaciones UIAF",
                    "macro_dominio": "Transversal",
                    "micro_competencia": "Lavado de Activos",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: El auditor de la DIAN identifica que el dinero de las facturas apócrifas es enviado a paraísos fiscales en transacciones atípicas de fraccionamiento. PREGUNTA: Como servidor público de la DIAN, ante indicios serios de lavado de activos, ¿a qué entidad nacional debe remitir un Reporte de Operación Sospechosa (ROS) de manera inmediata?",
                    "options": {
                        "A": "A la Fiscalía General de la Nación directamente.",
                        "B": "A la Unidad de Información y Análisis Financiero (UIAF).",
                        "C": "Al Ministerio de Hacienda y Crédito Público."
                    },
                    "correct_key": "B",
                    "rationale": "Las entidades del Estado y servidores públicos, al amparo de la normativa contra el lavado de activos, deben reportar operaciones inusuales o sospechosas directamente a la UIAF (Unidad de Información y Análisis Financiero), que es la entidad de inteligencia financiera en Colombia encargada de analizar estos reportes."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Investigación Tributaria",
                    "topic": "OPEC 236769 - Levantamiento Velo Corporativo",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Evasión y Elusión",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: 'Asesorías Alfa S.A.S.' es una sociedad unipersonal constituida por un testaferro sin bienes, pero el beneficiario real de los dividendos es un gran contribuyente. PREGUNTA: De acuerdo con las normas de desestimación de la personalidad jurídica y abuso tributario, ¿cómo se denomina el mecanismo legal que permite desatender la personalidad jurídica de la sociedad para perseguir a los verdaderos beneficiarios de la evasión?",
                    "options": {
                        "A": "Levantamiento del Velo Corporativo (Abuso de las Formas Jurídicas).",
                        "B": "Declaratoria de Insolvencia Sobrevenida.",
                        "C": "Acción Pauliana de Reconstitución Patrimonial."
                    },
                    "correct_key": "A",
                    "rationale": "El levantamiento del velo corporativo (consagrado en materia tributaria a través de la cláusula general antiabuso del Artículo 869 y ss del E.T.) faculta a la DIAN a desconocer la estructura societaria cuando esta sea utilizada para la comisión de fraudes tributarios o abuso, imputando directamente las obligaciones y responsabilidades a los socios o beneficiarios efectivos."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Investigación Tributaria",
                    "topic": "OPEC 236769 - Intercambio de Información FATCA/CRS",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Fiscalización Aduanera",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: Para rastrear los fondos depositados en el exterior, el funcionario solicita información bancaria a través de convenios de cooperación internacional. PREGUNTA: ¿Cómo se denomina el estándar global de intercambio automático de información financiera liderado por la OCDE y suscrito por Colombia para la detección de activos ocultos en el exterior?",
                    "options": {
                        "A": "Estándar Común de Reporte (Common Reporting Standard - CRS).",
                        "B": "Tratado de Extradición y Asistencia Judicial Mútua.",
                        "C": "Declaración de Basilea sobre Control Financiero."
                    },
                    "correct_key": "A",
                    "rationale": "El CRS (Common Reporting Standard) es el modelo global de intercambio automático de información de cuentas financieras creado por la OCDE al cual está adherido Colombia, lo que le permite a la DIAN recibir reportes masivos de saldos e inversiones de colombianos en más de 100 países."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Detección de Evasión",
                    "topic": "OPEC 236769 - Norma General Antiabuso",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Evasión y Elusión",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: Durante la auditoría, la empresa constructora justifica la deducción afirmando que las transacciones con 'Asesorías Alfa S.A.S.' formalmente cumplen los requisitos estipulados en los contratos escritos. PREGUNTA: Al amparo del Artículo 869 del Estatuto Tributario, ¿cuál es el principio que faculta a la DIAN a reconfigurar la transacción por encima de las formas legales adoptadas por el contribuyente?",
                    "options": {
                        "A": "Prevalencia de la Sustancia Económica sobre la Forma Jurídica.",
                        "B": "Principio de Buena Fe Contractual del Comprador.",
                        "C": "Principio de Autonomía de la Voluntad Privada."
                    },
                    "correct_key": "A",
                    "rationale": "La norma general antiabuso (Artículo 869 E.T.) consagra que la administración tributaria puede desestimar las formas jurídicas cuando configuren un abuso en materia tributaria, prevaleciendo la realidad o sustancia económica y financiera de la transacción por encima del revestimiento formal del contrato."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Detección de Evasión",
                    "topic": "OPEC 236769 - Responsabilidad Solidaria de Socios",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Obligaciones Formales",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: La sociedad constructora es disuelta apresuradamente tras iniciarse la auditoría para evitar el cobro de la DIAN. PREGUNTA: De acuerdo con el Artículo 794 del Estatuto Tributario, ¿de qué forma responden los socios de sociedades limitadas o asimiladas frente a las deudas por impuestos de la sociedad?",
                    "options": {
                        "A": "De manera solidaria a prorrata de sus aportes o de su participación en la misma y por el tiempo durante el cual los hubieren poseído.",
                        "B": "Únicamente hasta el monto de las utilidades distribuidas en el último ejercicio fiscal.",
                        "C": "No tienen ningún tipo de responsabilidad personal dado que la sociedad tiene personalidad jurídica propia."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 794 del E.T. determina que en las sociedades de responsabilidad limitada y asimiladas, los socios responderán solidariamente por los impuestos, actualizaciones e intereses de la sociedad, a prorrata de sus aportes o de su participación en la misma y por el tiempo en que los hubieren poseído durante el período gravable respectivo."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Notificaciones Físicas a Direcciones",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Actos Administrativos",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: Un contribuyente implicado en la red no tiene buzón electrónico activo. PREGUNTA: De conformidad con el Artículo 565 del E.T., ¿a qué dirección postal debe remitir la DIAN el requerimiento o liquidación física para que se considere legalmente notificado?",
                    "options": {
                        "A": "A la dirección informada por el contribuyente en la última declaración de renta presentada o en la inscripción del RUT.",
                        "B": "A la dirección física que aparezca en el directorio telefónico municipal o Cámara de Comercio.",
                        "C": "A la oficina del representante legal suplente o de su contador público."
                    },
                    "correct_key": "A",
                    "rationale": "El Estatuto Tributario indica que los requerimientos, citaciones y demás actos de la administración deben notificarse a la dirección informada por el contribuyente en su última declaración tributaria, o en su defecto a la registrada en el Registro Único Tributario (RUT)."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Declaración de Renta Activos en Exterior",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Obligaciones Formales",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: El auditor de la DIAN identifica que el representante legal del consorcio posee cuentas en el extranjero que no incluyó en sus declaraciones de renta personales. PREGUNTA: ¿Qué declaración tributaria anual e informativa obligatoria debe presentar un residente fiscal en Colombia con activos en el exterior que superen las 2.000 UVT conforme al Artículo 607 del E.T.?",
                    "options": {
                        "A": "Declaración Anual de Activos en el Exterior (Formulario 160).",
                        "B": "Declaración Informativa de Precios de Transferencia.",
                        "C": "Reporte Anual de Cuentas Financieras Extranjeras."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 607 del E.T. obliga a todos los contribuyentes del impuesto sobre la renta que sean residentes fiscales en Colombia y posean activos en el exterior a presentar de forma anual la Declaración Anual de Activos en el Exterior utilizando el Formulario 160."
                }
            ]
        },
        {
            "id": "case-03-via-gubernativa",
            "title": "Caso 3: Vía Gubernativa, Recursos y Firmeza de los Actos Administrativos de Fiscalización",
            "text": "La sociedad 'Construcciones del Pacífico S.A.' recibe una Liquidación Oficial de Revisión por el año gravable 2023, en la cual la División de Liquidación de la DIAN le rechaza una deducción por amortización de intangibles de COP 800 millones y le impone una sanción por inexactitud. Inconforme con la decisión de la administración, la empresa decide agotar los recursos en la vía gubernativa antes de acudir a la jurisdicción contencioso-administrativa. El gestor a cargo debe analizar la procedencia del recurso de reconsideración, los términos legales para resolverlo, el silencio administrativo positivo y la posterior firmeza o pérdida de competencia por parte de la DIAN.",
            "difficulty": 3,
            "topic": "OPEC 236769 - Vía Gubernativa y Recursos en Fiscalización",
            "questions": [
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Recurso de Reconsideración Plazo",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Actos Administrativos",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: Tras notificarse la Liquidación Oficial de Revisión a 'Construcciones del Pacífico S.A.', su abogado prepara el recurso. PREGUNTA: De acuerdo con el Artículo 720 del Estatuto Tributario, ¿de cuánto tiempo dispone el contribuyente para interponer formalmente el Recurso de Reconsideración?",
                    "options": {
                        "A": "Dentro de los dos (2) meses siguientes a la fecha de notificación de la Liquidación Oficial de Revisión.",
                        "B": "Dentro de los diez (10) días hábiles siguientes a la entrega de la providencia.",
                        "C": "Dentro de los quince (15) días calendario contados a partir del recibo de la liquidación."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 720 del E.T. determina de forma taxativa que el recurso de reconsideración deberá interponerse por escrito ante la oficina competente de la DIAN, dentro de los dos (2) meses siguientes a la notificación de la Liquidación de Revisión."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Silencio Administrativo Positivo",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Actos Administrativos",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: El Recurso de Reconsideración fue radicado en tiempo, pero la DIAN tarda en proferir y notificar la resolución que lo resuelve debido a una congestión de expedientes. PREGUNTA: Conforme al Artículo 732 y 734 del Estatuto Tributario, ¿cuál es el plazo máximo que tiene la DIAN para resolver el Recurso de Reconsideración y qué ocurre si vence sin decisión notificada?",
                    "options": {
                        "A": "Un (1) año computado desde su interposición en debida forma; de no notificarse resolución en este plazo, opera el Silencio Administrativo Positivo a favor del contribuyente.",
                        "B": "Seis (6) meses prorrogables por tres más; si expira, la DIAN pierde competencia y el contribuyente debe acudir a la justicia ordinaria.",
                        "C": "Dos (2) años contados desde la radicación; si no hay respuesta, el recurso se entiende negado (silencio negativo)."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 732 del E.T. fija en un (1) año el término para resolver el recurso de reconsideración, contado desde su interposición en debida forma. El Artículo 734 consagra que si vence dicho término sin que se haya notificado la decisión, opera el silencio administrativo positivo, entendiéndose fallado el recurso a favor del recurrente."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Requisitos de Procedibilidad Recurso",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Actos Administrativos",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: Al revisar el Recurso de Reconsideración de la sociedad, el funcionario de la DIAN nota que fue firmado y presentado por el contador público de la empresa en lugar del representante legal o abogado. PREGUNTA: De acuerdo con los requisitos del Artículo 722 del Estatuto Tributario, ¿cuál de los siguientes es un requisito obligatorio de procedibilidad del recurso?",
                    "options": {
                        "A": "Interponerse por escrito directamente por el contribuyente o mediante apoderado debidamente constituido (quien debe ser abogado inscrito).",
                        "B": "Acompañar copia física firmada y autenticada de todos los libros de contabilidad del contribuyente.",
                        "C": "Haber cancelado previamente la totalidad de la sanción por inexactitud propuesta en el acto recurrido."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 722 del Estatuto Tributario señala que el recurso debe interponerse por escrito, expresando los motivos de inconformidad, y formularse por el contribuyente directamente o a través de apoderado legalmente constituido (quien por ley debe ser abogado con tarjeta profesional vigente para representar judicialmente)."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Auto de Inadmisión de Recurso",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Actos Administrativos",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: El abogado de la DIAN determina que el Recurso de Reconsideración omitió anexar el poder de representación y proyecta un Auto de Inadmisión. PREGUNTA: Conforme al Artículo 726 del E.T., ¿de cuánto tiempo dispone el contribuyente para subsanar los requisitos omitidos una vez notificado el Auto de Inadmisión?",
                    "options": {
                        "A": "Diez (10) días hábiles siguientes a la fecha de notificación del auto de inadmisión.",
                        "B": "Un (1) mes calendario contado desde la notificación del respectivo auto.",
                        "C": "Quince (15) días calendario siguientes al recibo del auto inadmitido."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 726 del E.T. prevé que la DIAN dictará Auto de Inadmisión si faltan los requisitos del Artículo 722, y otorgará al recurrente un plazo de diez (10) días hábiles para subsanar los defectos detectados y presentar nuevamente el recurso."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Recurso Contra Inadmisión",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Actos Administrativos",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: El contribuyente no subsana a tiempo y la DIAN confirma la inadmisión mediante Resolución de Rechazo. PREGUNTA: De acuerdo con el Artículo 728 del Estatuto Tributario, ¿qué recurso procede contra la Resolución de Rechazo del Recurso de Reconsideración?",
                    "options": {
                        "A": "Recurso de Reposición ante el mismo funcionario que profirió el rechazo.",
                        "B": "Recurso de Queja ante el superior inmediato del funcionario, interpuesto dentro de los cinco (5) días siguientes a la notificación.",
                        "C": "No procede recurso alguno en la vía gubernativa, quedando habilitada directamente la demanda contenciosa."
                    },
                    "correct_key": "B",
                    "rationale": "El Artículo 728 del E.T. prevé que contra la resolución que rechaza el recurso de reconsideración procede únicamente el Recurso de Queja ante el superior inmediato del funcionario que la dictó, dentro de los cinco (5) días siguientes a la notificación de la providencia."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Revocatoria Directa",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Actos Administrativos",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: Al contribuyente se le vencieron los términos para interponer el recurso de reconsideración y el acto cobró firmeza formal. PREGUNTA: Conforme al Artículo 736 del E.T., ¿qué mecanismo extraordinario puede interponer el contribuyente ante la propia DIAN para solicitar la anulación del acto manifiestamente ilegal dentro de los dos (2) años siguientes a su ejecutoria?",
                    "options": {
                        "A": "Acción de Revocatoria Directa.",
                        "B": "Recurso Extraordinario de Revisión.",
                        "C": "Acción Contenciosa de Nulidad y Restablecimiento."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 736 del Estatuto Tributario permite que los actos administrativos de la DIAN que se encuentren ejecutoriados sean revocados directamente por la propia administración a solicitud del contribuyente (o de oficio) bajo las causales del Código de Procedimiento Administrativo y de lo Contencioso Administrativo (CPACA)."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Firmeza Declaración con Pérdida",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Determinación de Impuestos",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: 'Construcciones del Pacífico S.A.' liquidó una pérdida fiscal en su declaración de renta del año 2023. PREGUNTA: De acuerdo con la Ley 2010 de 2019 y el Artículo 714 del E.T., ¿cuál es el término de firmeza especial aplicable a las declaraciones tributarias de renta en las cuales se liquiden o compensen pérdidas fiscales?",
                    "options": {
                        "A": "Cinco (5) años contados a partir del vencimiento del término para declarar o de la fecha de presentación extemporánea.",
                        "B": "Tres (3) años, idéntico al término general de firmeza de cualquier declaración sin saldos a favor.",
                        "C": "Diez (10) años contados desde la presentación de la respectiva declaración tributaria."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 714 del Estatuto Tributario indica que las declaraciones de renta en las cuales se liquiden o compensen pérdidas fiscales quedarán en firme en el término de cinco (5) años (en consonancia con el Artículo 147 del E.T. sobre el término para su compensación)."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Notificación por Conducta Concluyente",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Actos Administrativos",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: La DIAN envía la Liquidación de Revisión por correo certificado físico, pero la dirección postal contenía un error tipográfico. No obstante, el contribuyente acude a la DIAN a solicitar copia informal del expediente y responde manifestando conocer el contenido del acto administrativo. PREGUNTA: De acuerdo con las normas procesales del CPACA, ¿cómo se surte legalmente la notificación en este escenario?",
                    "options": {
                        "A": "Se configura una nulidad procesal insubsanable debiendo reiniciarse todo el trámite adeudado.",
                        "B": "Se surte por Conducta Concluyente, dándose por notificado en la fecha en que el contribuyente de forma expresa o tácita manifiesta conocer el acto.",
                        "C": "Se debe ignorar la comparecencia y proceder a publicar la notificación obligatoria en periódicos de circulación nacional."
                    },
                    "correct_key": "B",
                    "rationale": "La notificación por conducta concluyente opera cuando la persona interesada realiza alguna manifestación escrita o comparecencia procesal que devela de forma inequívoca el conocimiento integral y oportuno del acto administrativo, subsanando cualquier defecto formal de notificación previo."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Caducidad de la Acción de Nulidad",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Actos Administrativos",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: La DIAN expide resolución confirmatoria resolviendo negativamente el Recurso de Reconsideración, agotando la vía gubernativa. PREGUNTA: Según el CPACA, ¿de cuánto tiempo dispone el contribuyente para presentar la demanda contencioso-administrativa de Nulidad y Restablecimiento del Derecho antes de que opere la caducidad de la acción?",
                    "options": {
                        "A": "Cuatro (4) meses contados a partir del día siguiente al de la notificación del acto definitivo que agotó la vía gubernativa.",
                        "B": "Dos (2) meses siguientes a la ejecutoria del acto administrativo correspondiente.",
                        "C": "Seis (6) meses contados desde la notificación del acto expreso que resuelve el recurso."
                    },
                    "correct_key": "A",
                    "rationale": "El CPACA establece de manera inequívoca que la acción de Nulidad y Restablecimiento del Derecho caduca en el término de cuatro (4) meses contados a partir del día siguiente al de la notificación del acto expreso que decide el recurso o agota la vía gubernativa."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Firmeza Declaración con Beneficio Auditoría",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Determinación de Impuestos",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: 'Construcciones del Pacífico S.A.' incrementó su impuesto neto de renta del año 2024 en un 35% en relación con el año anterior y cumplió todos los requisitos exigidos por la ley para acceder al Beneficio de Auditoría. PREGUNTA: De acuerdo con las normas legales correspondientes, ¿cuál es el término de firmeza especial reducido que ampara a esta declaración?",
                    "options": {
                        "A": "Seis (6) meses siguientes a la fecha de su presentación oportuna.",
                        "B": "Doce (12) meses contados a partir del vencimiento del plazo para declarar.",
                        "C": "Un (1) mes calendario contado desde la fecha de presentación de la declaración."
                    },
                    "correct_key": "A",
                    "rationale": "Las normas de beneficio de auditoría (por ejemplo, consagradas en el Artículo 689-3 del E.T. para periodos aplicables) indican que cuando se incrementa el impuesto neto de renta en al menos un porcentaje determinado (e.g. 35%), la declaración quedará en firme a los seis (6) meses siguientes a su presentación oportuna."
                }
            ]
        },
        {
            "id": "case-04-devoluciones-sancionatorio",
            "title": "Caso 4: Devoluciones Improcedentes, Saldos a Favor y Pliegos de Cargos Sancionatorios",
            "text": "La multinacional 'Exportaciones Andinas Ltda.' solicita ante la División de Devoluciones de la Seccional de Impuestos de Cali la devolución de un saldo a favor acumulado en sus declaraciones del Impuesto sobre las Ventas (IVA) por valor de COP 1.500 millones, derivado de exportaciones calificadas exentas con derecho a devolución. Tras realizar la auditoría previa a la devolución, el gestor de fiscalización descubre que la empresa sustentó el 40% de sus saldos descontables en retenciones inexistentes e importaciones ficticias que nunca ingresaron a la aduana nacional. La DIAN no solo rechaza la devolución, sino que decide proferir un Pliego de Cargos e imponer la severa Sanción por Devolución Improcedente.",
            "difficulty": 3,
            "topic": "OPEC 236769 - Devoluciones Improcedentes e IVA Descontable",
            "questions": [
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Término Devolución Oportuna",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Devoluciones y Compensaciones",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: Tras radicar en debida forma la solicitud de devolución del saldo a favor de IVA por parte de 'Exportaciones Andinas Ltda.', el gestor de la DIAN debe controlar los términos legales. PREGUNTA: De conformidad con el Artículo 855 del Estatuto Tributario, ¿cuál es el plazo general máximo que tiene la DIAN para devolver los saldos a favor aprobados?",
                    "options": {
                        "A": "Dentro de los cincuenta (50) días siguientes a la fecha de la solicitud presentada en debida forma.",
                        "B": "Dentro de los treinta (30) días hábiles posteriores a la radicación de la documentación completa.",
                        "C": "Dentro de los quince (15) días siguientes a la solicitud de devolución oportuna."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 855 del Estatuto Tributario señala de manera expresa que la administración tributaria dispone de un término máximo de cincuenta (50) días para devolver los saldos a favor liquidados en declaraciones de renta o de IVA, contados a partir de la fecha de presentación en debida forma."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Auto de Suspensión de Términos",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Devoluciones y Compensaciones",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: El auditor de la DIAN encuentra inconsistencias serias y requiere suspender los términos de devolución para practicar una investigación profunda en el domicilio de los proveedores de la multinacional. PREGUNTA: De acuerdo con el Artículo 857-1 del E.T., ¿en cuánto tiempo y mediante qué acto administrativo se pueden suspender los términos del proceso de devolución mientras se adelanta la investigación de fiscalización?",
                    "options": {
                        "A": "Hasta por un máximo de noventa (90) días, mediante la expedición de un Auto de Suspensión de Términos debidamente motivado.",
                        "B": "Hasta por sesenta (60) días prorrogables por otros treinta, decretado mediante Auto de Apertura de Investigación previa.",
                        "C": "Por un término improrrogable de seis (6) meses mediante providencia administrativa irrecurrible."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 857-1 del E.T. faculta a la DIAN a decretar la suspensión del término para devolver hasta por un plazo máximo de noventa (90) días, proferido mediante Auto de Suspensión de Términos, si se detectan indicios de inexactitud o evasión en los saldos a favor reclamados."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Régimen Sancionatorio",
                    "topic": "OPEC 236769 - Sanción Devolución Improcedente Tarifa",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Sanciones Tributarias",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: El proceso de fiscalización confirma que la multinacional obtuvo de manera fraudulenta y previa una devolución que ya fue consignada en sus cuentas. PREGUNTA: Conforme al Artículo 670 del Estatuto Tributario, ¿cuál es la tarifa de la sanción por devolución o compensación improcedente aplicable sobre las sumas devueltas o compensadas de forma indebida?",
                    "options": {
                        "A": "Equivale al 100% de las sumas devueltas o compensadas improcedentemente, incrementado al 200% si se utilizaron documentos falsos.",
                        "B": "Equivale al 50% de las sumas devueltas de forma indebida, adicionando un recargo del 10% anual de intereses.",
                        "C": "Equivale al 20% del valor total determinado en el pliego de cargos correspondiente."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 670 del E.T. consagra que las devoluciones o compensaciones improcedentes serán objeto de reintegro de las sumas devueltas más la imposición de una sanción equivalente al cien por ciento (100%) de dicho valor, el cual se incrementará al doscientos por ciento (200%) en caso de comprobarse la utilización de documentos falsos o maniobras fraudulentas."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Pliego de Cargos Término Respuesta",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Actos Administrativos",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: El auditor de la DIAN notifica Pliego de Cargos a la multinacional proponiendo la sanción de devolución improcedente. PREGUNTA: De acuerdo con el Artículo 670 y las normas de procedimiento aplicables, ¿cuál es el plazo de que dispone la sociedad para dar respuesta por escrito y presentar sus descargos frente al Pliego de Cargos?",
                    "options": {
                        "A": "Un (1) mes contado a partir de la fecha de notificación del Pliego de Cargos.",
                        "B": "Diez (10) días hábiles contados a partir del día siguiente al de la notificación.",
                        "C": "Quince (15) días calendario siguientes al recibo de la comunicación."
                    },
                    "correct_key": "A",
                    "rationale": "Las normas generales de procedimiento de imposición de sanciones (en particular el trámite del Pliego de Cargos y lo consagrado de forma análoga en el Artículo 670 E.T.) conceden un término de un (1) mes calendario al contribuyente para responder formalmente formulando descargos y solicitando pruebas."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Régimen Sancionatorio",
                    "topic": "OPEC 236769 - Término de Prescripción Sanción",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Sanciones Tributarias",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: La DIAN pretende imponer una sanción por irregularidades en libros de contabilidad detectada durante la auditoría. PREGUNTA: Conforme al Artículo 638 del Estatuto Tributario, ¿cuál es el término de prescripción legal que tiene la DIAN para formular pliego de cargos e imponer sanciones independientes de las liquidaciones oficiales?",
                    "options": {
                        "A": "Dos (2) años contados a partir de la fecha en que se presentó la declaración en que se cometió la infracción o cesó la conducta sancionable.",
                        "B": "Tres (3) años contados desde la ocurrencia de los hechos u omisiones constitutivas de la infracción.",
                        "C": "Cinco (5) años computados desde la fecha de notificación del requerimiento especial."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 638 del Estatuto Tributario señala que la facultad para imponer sanciones tributarias de forma independiente prescribe en el término de dos (2) años contados desde la fecha en que se presentó la declaración en que se cometió la infracción o cesó la conducta sancionable. En caso de no requerirse declaración, se cuenta desde la ocurrencia de los hechos."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Régimen Sancionatorio",
                    "topic": "OPEC 236769 - Sanción de Clausura del Establecimiento",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Sanciones Tributarias",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: Durante la auditoría a una de las sucursales comerciales de la multinacional, el funcionario comprueba que la empresa omitió de forma deliberada la expedición de facturas de venta electrónicas a sus clientes minoristas. PREGUNTA: Según el Artículo 657 del E.T., ¿cuál es la sanción accesoria o de clausura que puede imponer la DIAN ante la no expedición sistemática de la factura de venta?",
                    "options": {
                        "A": "Sanción de clausura o cierre del establecimiento de comercio, oficina o consultorio por un término de tres (3) días calendario.",
                        "B": "Sanción pecuniaria equivalente al 50% de las ventas brutas del mes respectivo sin ordenar el cierre físico.",
                        "C": "Clausura indefinida hasta tanto el contribuyente implemente el software de facturación."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 657 del Estatuto Tributario consagra de manera expresa la sanción de clausura o cierre del establecimiento por un término de tres (3) días cuando se compruebe la no expedición de la factura de venta obligatoria."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Corrección que Disminuye Valor",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Obligaciones Formales",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: La multinacional decide corregir voluntariamente su declaración de renta disminuyendo el saldo a favor inicialmente liquidado para evitar la apertura de una investigación formal por la DIAN. PREGUNTA: De acuerdo con el Artículo 589 del Estatuto Tributario, ¿cuál es el término de que dispone un contribuyente para corregir su declaración tributaria cuando dicha corrección implique disminuir el valor a pagar o aumentar el saldo a favor?",
                    "options": {
                        "A": "Dentro del año (1) siguiente al vencimiento del término para presentar la declaración.",
                        "B": "Dentro de los tres (3) años siguientes al vencimiento del término para declarar, siempre que no se haya notificado requerimiento especial.",
                        "C": "Dentro de los dos (2) años siguientes a la presentación de la declaración inicial."
                    },
                    "correct_key": "B",
                    "rationale": "El Artículo 589 del E.T. prevé que para corregir las declaraciones disminuyendo el valor a pagar o aumentando el saldo a favor, el contribuyente debe presentar la solicitud de corrección respectiva dentro de los tres (3) años siguientes al vencimiento del plazo para declarar, estando sujeta a la firmeza de la declaración."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Devolución Automática Requisitos",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Devoluciones y Compensaciones",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: Un contribuyente pyme solicita la devolución automática de su saldo a favor de renta del año 2024. PREGUNTA: De acuerdo con las normas tributarias reglamentarias de la DIAN, ¿cuál es el requisito fundamental sobre facturación electrónica exigido para acceder a la Devolución Automática de saldos a favor?",
                    "options": {
                        "A": "Que más del ochenta y cinco por ciento (85%) de los costos, gastos o IVA descontable declarados provengan de proveedores que expidan factura electrónica de venta.",
                        "B": "Haber facturado electrónicamente al menos el 50% de sus ingresos anuales.",
                        "C": "Que la totalidad de sus clientes nacionales estén registrados en el RUT con correo electrónico vigente."
                    },
                    "correct_key": "A",
                    "rationale": "El Decreto Reglamentario en armonía con el Estatuto Tributario establece que para acceder a la devolución automática del saldo a favor, se requiere que más del 85% de los costos, deducciones e impuestos descontables estén soportados en facturas electrónicas válidamente emitidas y registradas."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Régimen Sancionatorio",
                    "topic": "OPEC 236769 - Sanción de Inexactitud por Pasivos Ficticios",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Sanciones Tributarias",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: Durante el cruce de información en el proceso de devolución, se comprueba que 'Exportaciones Andinas Ltda.' registró deudas a favor de una filial extranjera ubicada en Panamá sin soporte real. PREGUNTA: Conforme al Artículo 648 del E.T., ¿cuál es el porcentaje de sanción por inexactitud aplicable cuando se liquiden pasivos inexistentes con propósitos de evasión en renta?",
                    "options": {
                        "A": "El 100% de la diferencia o impuesto determinado oficialmente por la glosa respectiva.",
                        "B": "El 160% aplicable de manera especial a maniobras que utilicen pasivos ficticios u operaciones simuladas.",
                        "C": "El 200% del valor total de la deuda simulada en la contabilidad."
                    },
                    "correct_key": "A",
                    "rationale": "Con las modificaciones normativas de la Ley de Reforma Tributaria 2277 de 2022, la sanción general por inexactitud se estandarizó en el cien por ciento (100%) sobre la diferencia liquidada. (Tradicionalmente el uso de pasivos inexistentes acarreaba una tarifa del 160%, la cual fue reducida al 100% general de manera legislativa, eliminando el trato especial gravoso salvo casos penales específicos)."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Rechazo de Solicitud Devolución",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Devoluciones y Compensaciones",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: Al revisar la solicitud de saldo a favor de IVA presentada por la multinacional, el funcionario nota que el saldo a favor ya había sido objeto de una compensación tributaria previa por otra seccional. PREGUNTA: De acuerdo con el Artículo 857 del Estatuto Tributario, ¿bajo qué figura procesal formal debe actuar la DIAN frente a esta solicitud de saldo ya extinguido?",
                    "options": {
                        "A": "Auto de Rechazo Definitivo de la solicitud de devolución.",
                        "B": "Auto de Inadmisión subsanable dentro de los quince (15) días siguientes.",
                        "C": "Resolución de Desistimiento Tácito y archivo de las actuaciones."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 857 del E.T. determina taxativamente las causales de rechazo definitivo de las solicitudes de devolución o compensación, figurando entre ellas el hecho de que el saldo a favor solicitado ya hubiere sido devuelto, compensado o imputado anteriormente."
                }
            ]
        },
        {
            "id": "case-05-inspeccion-pruebas",
            "title": "Caso 5: Práctica de Pruebas, Visitas de Inspección Tributaria y Registro e Indicios Legales",
            "text": "La División de Fiscalización de la Seccional de Impuestos de Medellín expide un Auto de Inspección Tributaria contra la distribuidora comercial 'Ferreterías Asociadas del Valle S.A.' con el fin de verificar sus inventarios físicos y constatar presuntos fraudes de omisión de ingresos por ventas en efectivo. El equipo de gestores de la DIAN se desplaza al domicilio social de la empresa para practicar la visita de inspección y registro de libros contables. El contribuyente intenta impedir el acceso a los servidores informáticos argumentando reserva comercial de sus bases de datos de facturación. El gestor de la DIAN debe aplicar correctamente el régimen de pruebas, valorar indicios, levantar actas formales y manejar la resistencia a la inspección conforme a la ley.",
            "difficulty": 3,
            "topic": "OPEC 236769 - Práctica de Pruebas e Inspección Tributaria",
            "questions": [
                {
                    "track": "FUNCIONAL",
                    "competency": "Régimen Probatorio",
                    "topic": "OPEC 236769 - Inspección Tributaria Auto",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Procedimiento Tributario",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: Para iniciar la visita oficial de fiscalización, el equipo de auditores debe notificar el acto que decreta la diligencia. PREGUNTA: Según el Artículo 779 del Estatuto Tributario, ¿con qué acto administrativo formal y motivado se decreta válidamente la realización de una Inspección Tributaria?",
                    "options": {
                        "A": "Auto de Inspección Tributaria de Trámite Notificado.",
                        "B": "Resolución Sanción por Resistencia Tributaria.",
                        "C": "Citación de Comparecencia Inmediata del Contribuyente."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 779 del E.T. consagra que la DIAN podrá decretar la práctica de una Inspección Tributaria mediante Auto de Trámite (Auto de Inspección Tributaria), el cual debe ser debidamente notificado antes de iniciar las diligencias en las dependencias."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Resistencia a la Inspección Sanción",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Sanciones Tributarias",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: El representante legal de la distribuidora obstaculiza físicamente el acceso al archivo y se niega a suministrar la clave de los servidores contables al equipo fiscalizador. PREGUNTA: Conforme al Artículo 653 y concordantes del E.T., ¿a qué sanción o trámite de apremio se expone el contribuyente por oponerse e impedir la realización de la inspección?",
                    "options": {
                        "A": "Imposición de una Sanción por no enviar Información o por obstrucción que puede ascender hasta 7.500 UVT y levantamiento de un acta de resistencia para presunción de ingresos omitidos.",
                        "B": "Clausura inmediata de la empresa por 10 días ordenado de facto por el auditor sin requerir orden judicial.",
                        "C": "Denuncia penal por desacato civil con arresto domiciliario del representante legal."
                    },
                    "correct_key": "A",
                    "rationale": "La obstrucción y resistencia a las visitas de fiscalización e inspección tributaria de la DIAN constituye una grave infracción a los deberes formales regulados en el régimen sancionatorio (Artículo 651 y ss). El auditor levantará Acta de Resistencia, lo que dará lugar a la imposición de multas por no suministrar información (hasta 7.500 UVT) y habilita indicios en contra."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Régimen Probatorio",
                    "topic": "OPEC 236769 - Pruebas Indiciarias",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Procedimiento Tributario",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: Al inspeccionar la bodega del distribuidor, el auditor de la DIAN constata una diferencia material significativa entre el inventario físico real y el inventario registrado en la contabilidad oficial. PREGUNTA: De acuerdo con el Artículo 758 del Estatuto Tributario, ¿qué tipo de presunción legal opera a favor de la DIAN cuando se constata una diferencia física de inventarios?",
                    "options": {
                        "A": "Se presume que la diferencia de inventarios constituye ingresos por ventas omitidas del respectivo período gravable.",
                        "B": "Se presume la comisión del delito aduanero de contrabando de mercancías.",
                        "C": "Se presume la buena fe del contribuyente y se ordena una reclasificación sin repercusión impositiva."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 758 del Estatuto Tributario consagra la presunción por diferencia de inventarios. Determina que cuando se constate una diferencia física en inventarios, se presumirá que dicha diferencia representa ventas u operaciones gravadas que fueron omitidas en las declaraciones tributarias."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Régimen Probatorio",
                    "topic": "OPEC 236769 - Acta de Visita Valor Probatorio",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Procedimiento Tributario",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: Al finalizar la visita de inspección, el gestor de la DIAN redacta un Acta de Visita donde consigna todos los hechos y hallazgos encontrados en presencia del contribuyente. PREGUNTA: Según el Artículo 781 del Estatuto Tributario, ¿cuál es el valor probatorio que ostentan las Actas de Visita levantadas por los funcionarios competentes de la DIAN?",
                    "options": {
                        "A": "Hacen fe pública y constituyen prueba plena de los hechos constatados en ellas, salvo que se demuestre su falsedad material o ideológica.",
                        "B": "Constituyen una prueba meramente sumaria o indicativa que requiere confirmación pericial posterior.",
                        "C": "Carecen de valor probatorio hasta tanto sean ratificadas por una resolución de liquidación en firme."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 781 del E.T. determina que los hechos consignados en las actas de visita levantadas por los funcionarios de la administración tributaria hacen fe de su ocurrencia y constituyen prueba plena de los mismos, a menos que se pruebe la falsedad o error de los hechos allí registrados."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Régimen Probatorio",
                    "topic": "OPEC 236769 - Exhibición de Libros de Contabilidad",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Obligaciones Formales",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: El gestor de la DIAN le exige formalmente al representante de la distribuidora la presentación inmediata de los libros oficiales de contabilidad físicos o del software contable registrado. PREGUNTA: Conforme al Artículo 780 del Estatuto Tributario, ¿quién tiene la carga de la prueba para desvirtuar las glosas si el contribuyente se niega a exhibir los libros de contabilidad al funcionario de la DIAN?",
                    "options": {
                        "A": "Se invierte la carga de la prueba, presumiéndose ciertos los hechos imputados por la DIAN y no se admitirá prueba posterior al contribuyente sobre los puntos no registrados.",
                        "B": "La DIAN conserva la obligación de conseguir pruebas por otros medios sin poder sancionar la no exhibición.",
                        "C": "La contabilidad se presume correcta y la DIAN debe buscar un perito judicial contable externo."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 780 indica que la no exhibición de los libros contables cuando el funcionario lo solicite constituye un indicio grave en contra del contribuyente y faculta a la DIAN a presumir como verdaderas las glosas imputadas, perdiéndose la oportunidad de invocar la prueba contable a su favor en etapas posteriores."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Régimen Probatorio",
                    "topic": "OPEC 236769 - Auto de Registro y Aseguramiento",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Procedimiento Tributario",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: El equipo de fiscalización sospecha que la distribuidora guarda un doble software de contabilidad ('contabilidad paralela') oculto en una caja fuerte dentro de la oficina del gerente. PREGUNTA: Conforme al Artículo 779-1 del E.T., ¿qué acto administrativo especial y con qué requisitos formales se requiere para autorizar el allanamiento y registro de las oficinas y bodegas con aseguramiento de pruebas?",
                    "options": {
                        "A": "Auto de Registro y Aseguramiento, proferido de manera motivada por el Director de Impuestos o Directores Seccionales competentes.",
                        "B": "Una orden judicial verbal proferida por un Fiscal Delegado ante la justicia penal ordinaria.",
                        "C": "Un oficio simple firmado por el auditor líder que encabeza la comisión de visita."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 779-1 del E.T. determina que para el registro físico de bodegas, establecimientos y oficinas de los contribuyentes con el fin de asegurar pruebas tributarias, se requiere expedir un Auto de Registro y Aseguramiento de manera motivada por parte de las autoridades competentes (Directores de Impuestos o Seccionales)."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Régimen Probatorio",
                    "topic": "OPEC 236769 - Declaraciones de Terceros",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Procedimiento Tributario",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: Durante la inspección, los auditores entrevistan a dos ex-empleados del distribuidor, quienes rinden testimonio formal sobre la existencia de ventas en efectivo no facturadas. PREGUNTA: De acuerdo con las normas procesales tributarias del Estatuto Tributario, ¿bajo qué formalidad debe rendirse la declaración de terceros para que sea admisible como prueba plena en el expediente?",
                    "options": {
                        "A": "Debe rendirse bajo juramento, levantando acta escrita y firmada por el compareciente ante el funcionario de la DIAN.",
                        "B": "Basta con una grabación de audio anónima tomada por los funcionarios en el establecimiento.",
                        "C": "Requiere ser certificada exclusivamente por una notaría pública del mismo domicilio comercial."
                    },
                    "correct_key": "A",
                    "rationale": "El Estatuto Tributario y las normas reglamentarias indican que las declaraciones de terceros o testimonios en materia fiscal deben ser tomadas bajo la gravedad del juramento por los funcionarios de fiscalización competentes, con el fin de garantizar la legalidad e idoneidad probatoria del testimonio."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Régimen Probatorio",
                    "topic": "OPEC 236769 - Indicio Grave por Inconsistencias",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Procedimiento Tributario",
                    "difficulty": 3,
                    "stem": "SITUACIÓN: El contribuyente presenta facturas electrónicas que no coinciden en numeración ni fechas con los despachos reportados por las transportadoras. PREGUNTA: De acuerdo con la teoría probatoria aplicable en la DIAN, ¿cómo se califica la contradicción ostensible entre las pruebas documentales presentadas por el contribuyente y la realidad fáctica demostrada por la administración?",
                    "options": {
                        "A": "Configura un Indicio Grave contra la veracidad de las declaraciones tributarias del contribuyente.",
                        "B": "Constituye un error puramente subsanable del transportador sin valor procesal contra la empresa.",
                        "C": "Representa una presunción de inocencia automática que obliga a la DIAN a archivar el expediente."
                    },
                    "correct_key": "A",
                    "rationale": "Las contradicciones palmarias y de fondo entre los documentos del contribuyente y los hallazgos de la administración se valoran en el expediente bajo la sana crítica como Indicios Graves, los cuales sumados de forma coherente permiten desvirtuar la presunción de veracidad consagrada en el Artículo 746 del E.T."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Régimen Probatorio",
                    "topic": "OPEC 236769 - Ineficacia de la Declaración Retenciones",
                    "macro_dominio": "Tributario",
                    "micro_competencia": "Obligaciones Formales",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: Al cruzar las cuentas del distribuidor, el gestor comprueba que la empresa presentó la declaración de retenciones en la fuente a tiempo, pero omitió realizar el pago de la misma. PREGUNTA: Conforme al Artículo 580-1 del Estatuto Tributario, ¿cuál es la consecuencia legal inmediata de presentar una declaración de retención en la fuente sin pago total dentro del plazo establecido?",
                    "options": {
                        "A": "La declaración de retención se entiende ineficaz de pleno derecho, sin necesidad de acto administrativo que así lo declare.",
                        "B": "La declaración se considera válida, pero se generan recargos por extemporaneidad equivalentes al 5% mensual.",
                        "C": "La DIAN procede a embargar de inmediato las cuentas de la empresa sin notificar mandamiento de pago."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 580-1 del E.T. determina de manera expresa que las declaraciones de retención en la fuente presentadas sin pago total dentro de los términos establecidos carecen de efectos legales (son ineficaces de pleno derecho), con la excepción de saldos a favor pendientes que cumplan los requisitos allí establecidos."
                },
                {
                    "track": "FUNCIONAL",
                    "competency": "Procedimiento Tributario",
                    "topic": "OPEC 236769 - Reserva de la Información Tributaria",
                    "macro_dominio": "Transversal",
                    "micro_competencia": "Ética e Integridad",
                    "difficulty": 2,
                    "stem": "SITUACIÓN: Un funcionario de la DIAN es abordado por un periodista local que le ofrece dinero a cambio de revelarle detalles sobre el proceso de fiscalización a 'Ferreterías Asociadas del Valle S.A.'. PREGUNTA: Según el Artículo 583 del Estatuto Tributario, ¿cuál es el deber fundamental de reserva que obliga a los servidores de la DIAN respecto a las bases de datos de los contribuyentes?",
                    "options": {
                        "A": "La información tributaria respecto a las bases gravables, ingresos y deducciones declarados goza de reserva absoluta y su violación acarrea destitución del cargo.",
                        "B": "La reserva es parcial y el servidor público puede revelar detalles si se trata de una empresa de interés público municipal.",
                        "C": "No existe reserva tributaria dado que la información de los impuestos es de carácter público por el principio de transparencia."
                    },
                    "correct_key": "A",
                    "rationale": "El Artículo 583 del E.T. establece el deber de reserva de las declaraciones tributarias de los contribuyentes, señalando que los datos declarados tienen carácter estrictamente confidencial. La revelación de dicha información por parte del servidor público constituye una falta gravísima que genera destitución e inhabilidad general."
                }
            ]
        }
    ]
    
    # Conectarse a la Base de Datos
    db = SessionLocal()
    try:
        cases_inserted = 0
        questions_inserted = 0
        
        # Obtener el ID del usuario César
        # El diagnóstico anterior determinó que ID=2 es el usuario 'cesar'
        cesar_id = 2
        
        for c_data in CASES_DATA:
            # Comprobar si el Caso ya existe
            existing_case = db.query(CaseStudy).filter_by(title=c_data["title"]).first()
            
            if existing_case:
                print(f"ℹ️ El Caso '{c_data['title']}' ya existe. ID={existing_case.id}. Saltando...")
                case_obj = existing_case
            else:
                case_obj = CaseStudy(
                    id=str(uuid.uuid4()),
                    title=c_data["title"],
                    text=c_data["text"],
                    difficulty=c_data["difficulty"],
                    topic=c_data["topic"],
                    created_at=datetime.datetime.utcnow()
                )
                db.add(case_obj)
                db.flush() # Para obtener el ID generado del caso si no tenía
                cases_inserted += 1
                print(f"✅ Caso creado: '{c_data['title']}'")
            
            # Procesar preguntas asociadas al caso
            for q_data in c_data["questions"]:
                h = compute_hash(q_data["stem"])
                
                # Comprobar duplicado por hash de stem
                existing_q = db.query(Question).filter_by(hash_norm=h).first()
                if existing_q:
                    # Si ya existe, podemos omitir o asociarlo al caso actual si difiere
                    continue
                
                new_q = Question(
                    question_id=str(uuid.uuid4()),
                    case_id=case_obj.id,
                    track=q_data["track"],
                    competency=q_data["competency"],
                    topic=q_data["topic"],
                    macro_dominio=q_data["macro_dominio"],
                    micro_competencia=q_data["micro_competencia"],
                    difficulty=q_data["difficulty"],
                    question_type="SITUATIONAL",
                    stem=q_data["stem"],
                    options_json=q_data["options"],
                    correct_key=q_data["correct_key"],
                    rationale=q_data["rationale"],
                    source_refs="Inyección Especial Antigravity - OPEC 236769",
                    created_at=datetime.datetime.utcnow(),
                    hash_norm=h,
                    is_verified=True
                )
                db.add(new_q)
                questions_inserted += 1
        
        db.commit()
        print(f"\n🎉 ¡Proceso finalizado con éxito!")
        print(f"📊 Casos Nuevos Insertados: {cases_inserted}")
        print(f"📊 Preguntas Nuevas Insertadas: {questions_inserted}")
        
    except Exception as e:
        db.rollback()
        print(f"🔥 Error durante la inserción en la base de datos: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    insert_custom_questions()
