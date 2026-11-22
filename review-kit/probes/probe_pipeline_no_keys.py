import asyncio, os, sys
sys.path.insert(0,'.')
os.environ.pop("GEMINI_API_KEY",None); os.environ.pop("GROQ_API_KEY",None)
from sqlalchemy.orm import sessionmaker
from app.main import load_profile
from app.db.session import init_db
from app.db.repos import SQLAlchemyJobRepo, SQLAlchemyInboxRepo
from app.llm.provider import ProductionLLMProvider
from app.pipeline.extract import ProductionExtractor
from app.pipeline.linkfetch import ProductionLinkFetcher
from app.pipeline.prefilter import ProductionPreFilter
from app.pipeline.rules.dedupe import ProductionDeduper
from app.pipeline.rules.engine import ProductionRulesEngine
from app.pipeline.rules.scoring import ProductionScorer
from app.cv.builder import ProductionCVBuilder
from app.mail.sender import ProductionMailer
from app.worker.pipeline import PipelineEngine
from contracts.models import IncomingMessage

async def main():
    eng=init_db(); 
    from app.db.session import create_db_engine
    eng=create_db_engine(); 
    from app.db.models import Base; Base.metadata.create_all(eng)
    sf=sessionmaker(bind=eng)
    llm=ProductionLLMProvider()
    p=PipelineEngine(ProductionPreFilter(),ProductionExtractor(llm),ProductionLinkFetcher(),ProductionRulesEngine(),ProductionScorer(),ProductionDeduper(),ProductionCVBuilder(),ProductionMailer(),SQLAlchemyJobRepo(sf),SQLAlchemyInboxRepo(sf),load_profile())
    tests={
     "NOISE_birthday":"Happy birthday to our batchmate Ali! Wishing you the best, party at 8pm everyone should join us tonight",
     "SALES_job_Lahore":"We are hiring Sales Executive in Lahore onsite. Send CV to hr@somecompany.pk",
     "F1_paysys":"We're Hiring – *DevOps Engineer!* Paysys Labs Karachi (On-site) 0–1 Years Fresh Graduates. Send your updated CV to hiring@paysyslabs.com with the subject line \"DevOps Engineer – Application\".",
    }
    for k,t in tests.items():
        try:
            cards=await p.process_message(IncomingMessage(source_id=k,chat_id="x@g.us",chat_name="TestGroup",raw_text=t))
            print(k,"->",[(c.role.title,c.role.company,c.role.apply_email,c.tier.value,c.score,c.role.exact_subject) for c in cards])
        except Exception as e:
            print(k,"-> [Properly handled without fake cards:", type(e).__name__, "]")
asyncio.run(main())
