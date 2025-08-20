from apscheduler.schedulers.background import BackgroundScheduler

def start_scheduler(digest_job, hour: int, minute: int):
    scheduler = BackgroundScheduler()
    scheduler.add_job(digest_job, "cron", hour=hour, minute=minute)
    scheduler.start()
    return scheduler
