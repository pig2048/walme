import os
import json
import time
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
import random
from colorama import Fore, Style, init
from tqdm import tqdm
import socket


init(autoreset=True)


BASE_URL = 'https://api.walme.io/waitlist/tasks'
PROFILE_URL = 'https://api.walme.io/user/profile'
COMPLETED_TASKS_FILE = 'completed_tasks.json'
TOKENS_FILE = 'tokens.txt'
PROXIES_FILE = 'proxies.txt'
CONFIG_FILE = 'config.json'
VERSION = "1.0.0"


DEFAULT_CONFIG = {
    "use_proxies": True,
    "max_concurrency": 3,
    "retry_attempts": 3,
    "delay_between_accounts": {
        "min": 2.0,
        "max": 5.0
    },
    "delay_between_tasks": {
        "min": 1.5,
        "max": 3.5
    },
    "log_to_file": True,
    "log_level": "INFO",
    "run_interval_hours": 24
}


SYMBOLS = {
    "success": f"{Fore.GREEN}✓{Style.RESET_ALL}",
    "error": f"{Fore.RED}✗{Style.RESET_ALL}",
    "info": f"{Fore.BLUE}ℹ{Style.RESET_ALL}",
    "warning": f"{Fore.YELLOW}⚠{Style.RESET_ALL}",
    "profile": f"{Fore.MAGENTA}👤{Style.RESET_ALL}",
    "task": f"{Fore.CYAN}📋{Style.RESET_ALL}",
    "processing": f"{Fore.YELLOW}⚙{Style.RESET_ALL}",
    "retry": f"{Fore.YELLOW}↻{Style.RESET_ALL}",
    "trophy": f"{Fore.YELLOW}🏆{Style.RESET_ALL}",
    "star": f"{Fore.YELLOW}★{Style.RESET_ALL}",
    "time": f"{Fore.CYAN}⏱{Style.RESET_ALL}",
    "rocket": f"{Fore.CYAN}🚀{Style.RESET_ALL}",
    "coin": f"{Fore.YELLOW}🪙{Style.RESET_ALL}",
    "chart": f"{Fore.GREEN}📈{Style.RESET_ALL}",
    "lock": f"{Fore.RED}🔒{Style.RESET_ALL}",
    "unlock": f"{Fore.GREEN}🔓{Style.RESET_ALL}",
    "config": f"{Fore.BLUE}⚙️{Style.RESET_ALL}",
    "daily": f"{Fore.GREEN}📅{Style.RESET_ALL}"
}


logger = None

def setup_logging(config):
    
    global logger
    
    
    logger = logging.getLogger("WalmeBot")
    
    
    if logger.hasHandlers():
        logger.handlers.clear()
    
    logger.setLevel(getattr(logging, config.get("log_level", "INFO")))
    
    
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, config.get("log_level", "INFO")))
    logger.addHandler(console_handler)
    
    
    if config.get("log_to_file", True):
        file_handler = logging.FileHandler("walme_bot.log", encoding='utf-8')
        file_handler.setLevel(getattr(logging, config.get("log_level", "INFO")))
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    
    logger.propagate = False
    
    return logger


def print_banner():
    banner = f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════╗
{Fore.CYAN}║          {Fore.WHITE}W A L M E  B O T  {Fore.YELLOW}★ {Fore.MAGENTA}E N H A N C E D{Fore.CYAN}       ║
{Fore.CYAN}║  {Fore.WHITE}Automated Tasks Management System v{VERSION}{Fore.CYAN}           ║
{Fore.CYAN}╚═══════════════════════════════════════════════════════╝
    """
    print(banner)


async def load_or_create_config():
    
    try:
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
            logger.info(f"{SYMBOLS['config']} {Fore.GREEN}Created default configuration file: {CONFIG_FILE}{Style.RESET_ALL}")
            return DEFAULT_CONFIG
            
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            
        
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
                
        logger.info(f"{SYMBOLS['config']} {Fore.WHITE}Loaded configuration from {CONFIG_FILE}{Style.RESET_ALL}")
        return config
    except Exception as e:
        logger.error(f"{SYMBOLS['error']} {Fore.RED}Failed to load config: {str(e)}. Using defaults.{Style.RESET_ALL}")
        return DEFAULT_CONFIG

async def load_tokens():
    
    try:
        if not os.path.exists(TOKENS_FILE):
            logger.error(f"{SYMBOLS['error']} {Fore.RED}Tokens file not found: {TOKENS_FILE}{Style.RESET_ALL}")
            return []
            
        with open(TOKENS_FILE, 'r') as f:
            tokens = [token.strip() for token in f.readlines() if token.strip()]
            
        if not tokens:
            logger.error(f"{SYMBOLS['error']} {Fore.RED}No tokens found in: {TOKENS_FILE}{Style.RESET_ALL}")
            return []
            
        logger.info(f"{SYMBOLS['info']} {Fore.WHITE}Loaded {len(tokens)} tokens from {TOKENS_FILE}{Style.RESET_ALL}")
        return tokens
    except Exception as e:
        logger.error(f"{SYMBOLS['error']} {Fore.RED}Failed to load tokens: {str(e)}{Style.RESET_ALL}")
        return []

async def load_proxies(use_proxies=True):
    
    if not use_proxies:
        logger.info(f"{SYMBOLS['info']} {Fore.WHITE}Proxy usage disabled in config. Running without proxies.{Style.RESET_ALL}")
        return []
        
    try:
        if not os.path.exists(PROXIES_FILE):
            logger.warning(f"{SYMBOLS['warning']} {Fore.YELLOW}Proxies file not found: {PROXIES_FILE}. Running without proxies.{Style.RESET_ALL}")
            return []
            
        with open(PROXIES_FILE, 'r') as f:
            proxies = [proxy.strip() for proxy in f.readlines() if proxy.strip()]
            
        if not proxies:
            logger.warning(f"{SYMBOLS['warning']} {Fore.YELLOW}No proxies found in: {PROXIES_FILE}. Running without proxies.{Style.RESET_ALL}")
            return []
            
        logger.info(f"{SYMBOLS['info']} {Fore.WHITE}Loaded {len(proxies)} proxies from {PROXIES_FILE}{Style.RESET_ALL}")
        return proxies
    except Exception as e:
        logger.warning(f"{SYMBOLS['warning']} {Fore.YELLOW}Failed to load proxies: {str(e)}. Running without proxies.{Style.RESET_ALL}")
        return []

async def load_completed_tasks():
    
    try:
        if not os.path.exists(COMPLETED_TASKS_FILE):
            return {}
            
        with open(COMPLETED_TASKS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"{SYMBOLS['warning']} {Fore.YELLOW}Failed to load completed tasks: {str(e)}. Starting with empty state.{Style.RESET_ALL}")
        return {}

async def save_completed_tasks(completed_tasks):
    
    try:
        with open(COMPLETED_TASKS_FILE, 'w') as f:
            json.dump(completed_tasks, f, indent=2)
    except Exception as e:
        logger.error(f"{SYMBOLS['error']} {Fore.RED}Failed to save completed tasks: {str(e)}{Style.RESET_ALL}")


async def fetch_profile(session, token, proxy=None, max_retries=3):
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    proxy_url = None
    if proxy:
        proxy_url = f"http://{proxy}" if not proxy.startswith(('http://', 'https://')) else proxy
        proxy_display = proxy.replace(":", "****:", 1) if ":" in proxy else proxy
    else:
        proxy_display = "None"
    
    for attempt in range(max_retries):
        try:
            async with session.get(PROFILE_URL, headers=headers, proxy=proxy_url, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    email = data.get('email', 'unknown')
                    nickname = data.get('nickname', 'unknown')
                    logger.info(f"{SYMBOLS['profile']} {Fore.GREEN}Profile fetched: {email} ({nickname}){Style.RESET_ALL}")
                    return {'email': email, 'nickname': nickname}
                else:
                    error_text = await response.text()
                    logger.error(f"{SYMBOLS['error']} {Fore.RED}Failed to fetch profile (HTTP {response.status}): {error_text}{Style.RESET_ALL}")
        except (aiohttp.ClientError, asyncio.TimeoutError, socket.gaierror) as e:
            if attempt < max_retries - 1:
                retry_delay = 2 ** attempt  
                logger.warning(f"{SYMBOLS['retry']} {Fore.YELLOW}Retrying profile fetch in {retry_delay}s ({attempt+1}/{max_retries}): {str(e)}{Style.RESET_ALL}")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"{SYMBOLS['error']} {Fore.RED}Failed to fetch profile after {max_retries} attempts: {str(e)}{Style.RESET_ALL}")
                raise
    
    raise Exception(f"Failed to fetch profile after {max_retries} attempts")

async def fetch_tasks(session, token, proxy=None, max_retries=3):
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    proxy_url = None
    if proxy:
        proxy_url = f"http://{proxy}" if not proxy.startswith(('http://', 'https://')) else proxy
    
    for attempt in range(max_retries):
        try:
            async with session.get(BASE_URL, headers=headers, proxy=proxy_url, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"{SYMBOLS['error']} {Fore.RED}Failed to fetch tasks (HTTP {response.status}): {error_text}{Style.RESET_ALL}")
        except (aiohttp.ClientError, asyncio.TimeoutError, socket.gaierror) as e:
            if attempt < max_retries - 1:
                retry_delay = 2 ** attempt  
                logger.warning(f"{SYMBOLS['retry']} {Fore.YELLOW}Retrying tasks fetch in {retry_delay}s ({attempt+1}/{max_retries}): {str(e)}{Style.RESET_ALL}")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"{SYMBOLS['error']} {Fore.RED}Failed to fetch tasks after {max_retries} attempts: {str(e)}{Style.RESET_ALL}")
                raise
    
    raise Exception(f"Failed to fetch tasks after {max_retries} attempts")

async def complete_task(session, task_id, token, proxy=None, max_retries=3):
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    proxy_url = None
    if proxy:
        proxy_url = f"http://{proxy}" if not proxy.startswith(('http://', 'https://')) else proxy
    
    for attempt in range(max_retries):
        try:
            async with session.patch(f"{BASE_URL}/{task_id}", headers=headers, proxy=proxy_url, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"{SYMBOLS['success']} {Fore.GREEN}Task {task_id} completed: {data.get('title', 'Unknown task')}{Style.RESET_ALL}")
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"{SYMBOLS['error']} {Fore.RED}Failed to complete task {task_id} (HTTP {response.status}): {error_text}{Style.RESET_ALL}")
        except (aiohttp.ClientError, asyncio.TimeoutError, socket.gaierror) as e:
            if attempt < max_retries - 1:
                retry_delay = 2 ** attempt  
                logger.warning(f"{SYMBOLS['retry']} {Fore.YELLOW}Retrying task completion in {retry_delay}s ({attempt+1}/{max_retries}): {str(e)}{Style.RESET_ALL}")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"{SYMBOLS['error']} {Fore.RED}Failed to complete task {task_id} after {max_retries} attempts: {str(e)}{Style.RESET_ALL}")
                raise
    
    raise Exception(f"Failed to complete task {task_id} after {max_retries} attempts")

async def daily_check_in(profile, completed_tasks):
    
    today = datetime.now().strftime("%Y-%m-%d")
    email = profile['email']
    
    if email not in completed_tasks:
        completed_tasks[email] = {"checkInDays": {}, "tasks": {}}
    
    if "checkInDays" not in completed_tasks[email]:
        completed_tasks[email]["checkInDays"] = {}
        
    if today not in completed_tasks[email]["checkInDays"]:
        day_count = len(completed_tasks[email]["checkInDays"]) + 1
        logger.info(f"{SYMBOLS['daily']} {Fore.YELLOW}{email} - Day {day_count}/7 - 7-Day Challenge: Boost Your XP - Check-in successful!{Style.RESET_ALL}")
        completed_tasks[email]["checkInDays"][today] = True
        
        if day_count >= 7:
            logger.info(f"{SYMBOLS['trophy']} {Fore.GREEN}{email} - 7-Day Challenge completed! XP Boost earned!{Style.RESET_ALL}")
    else:
        logger.info(f"{SYMBOLS['info']} {Fore.CYAN}{email} - Already checked in today ({today}){Style.RESET_ALL}")
    
    return completed_tasks

async def process_account(session, token, proxy, completed_tasks, config):
    
    try:
        
        logger.info(f"{SYMBOLS['info']} {Fore.WHITE}Fetching user profile...{Style.RESET_ALL}")
        profile = await fetch_profile(session, token, proxy, config.get("retry_attempts", 3))
        email = profile['email']
        
        
        completed_tasks = await daily_check_in(profile, completed_tasks)
        
        
        logger.info(f"{SYMBOLS['task']} {Fore.WHITE}{email} - Fetching tasks...{Style.RESET_ALL}")
        tasks = await fetch_tasks(session, token, proxy, config.get("retry_attempts", 3))
        logger.info(f"{SYMBOLS['task']} {Fore.WHITE}{email} - Fetched {len(tasks)} tasks{Style.RESET_ALL}")
        
        
        if "tasks" not in completed_tasks[email]:
            completed_tasks[email]["tasks"] = {}
            
        pending_tasks = [task for task in tasks if task['status'] == 'new' and str(task['id']) not in completed_tasks[email]["tasks"]]
        logger.info(f"{SYMBOLS['task']} {Fore.WHITE}{email} - Found {len(pending_tasks)} new pending tasks{Style.RESET_ALL}")
        
        
        for task in pending_tasks:
            logger.info(f"{SYMBOLS['processing']} {Fore.YELLOW}{email} - Processing task: {task.get('title', 'Unknown')} (ID: {task['id']}){Style.RESET_ALL}")
            
            if task.get('child') and len(task['child']) > 0:
                
                for child_task in task['child']:
                    if child_task['status'] == 'new' and str(child_task['id']) not in completed_tasks[email]["tasks"]:
                        await complete_task(session, child_task['id'], token, proxy, config.get("retry_attempts", 3))
                        completed_tasks[email]["tasks"][str(child_task['id'])] = True
                        
                        delay = random.uniform(
                            config.get("delay_between_tasks", {}).get("min", 1.0),
                            config.get("delay_between_tasks", {}).get("max", 3.0)
                        )
                        await asyncio.sleep(delay)
            else:
                
                await complete_task(session, task['id'], token, proxy, config.get("retry_attempts", 3))
                completed_tasks[email]["tasks"][str(task['id'])] = True
                
            
            delay = random.uniform(
                config.get("delay_between_tasks", {}).get("min", 1.5),
                config.get("delay_between_tasks", {}).get("max", 3.5)
            )
            await asyncio.sleep(delay)
        
        
        total_tasks = len(completed_tasks[email]["tasks"])
        total_days = len(completed_tasks[email]["checkInDays"])
        logger.info(f"{SYMBOLS['chart']} {Fore.MAGENTA}{email} - Account Summary: {total_tasks} tasks completed, {total_days} daily check-ins{Style.RESET_ALL}")
        
        return completed_tasks
    except Exception as e:
        logger.error(f"{SYMBOLS['error']} {Fore.RED}Account processing failed: {str(e)}{Style.RESET_ALL}")
        return completed_tasks

def generate_stats(completed_tasks):
    
    stats = {
        "total_accounts": len(completed_tasks),
        "total_tasks_completed": 0,
        "total_daily_checkins": 0,
        "accounts_with_7day_challenge": 0,
        "account_details": []
    }
    
    for email, data in completed_tasks.items():
        tasks_count = len(data.get("tasks", {}))
        checkins_count = len(data.get("checkInDays", {}))
        
        stats["total_tasks_completed"] += tasks_count
        stats["total_daily_checkins"] += checkins_count
        
        if checkins_count >= 7:
            stats["accounts_with_7day_challenge"] += 1
            
        stats["account_details"].append({
            "email": email,
            "tasks_completed": tasks_count,
            "daily_checkins": checkins_count,
            "challenge_completed": checkins_count >= 7
        })
    
    return stats

def save_stats(stats):
    
    try:
        with open('walme_stats.json', 'w') as f:
            json.dump(stats, f, indent=2)
        logger.info(f"{SYMBOLS['chart']} {Fore.GREEN}Statistics saved to walme_stats.json{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"{SYMBOLS['error']} {Fore.RED}Failed to save statistics: {str(e)}{Style.RESET_ALL}")

def display_countdown(next_run_time, config):
    
    try:
        
        while datetime.now() < next_run_time:
            remaining = next_run_time - datetime.now()
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            total_seconds = config.get("run_interval_hours", 24) * 3600
            elapsed_seconds = total_seconds - remaining.total_seconds()
            progress = (elapsed_seconds / total_seconds) * 100
            
            
            bar_length = 50
            filled_length = int(bar_length * progress / 100)
            bar = '=' * filled_length + '-' * (bar_length - filled_length)
            
            
            print(f"\r{SYMBOLS['time']} Next run in {hours:02d}h {minutes:02d}m {seconds:02d}s [{bar}] {progress:.1f}%", end='', flush=True)
            
            time.sleep(1)
            
        print("\n")  
        logger.info(f"{SYMBOLS['rocket']} {Fore.BLUE}Countdown complete. Starting next run...{Style.RESET_ALL}")
    except KeyboardInterrupt:
        print("\n")  
        logger.info(f"\n{SYMBOLS['info']} {Fore.YELLOW}Countdown interrupted. Press Ctrl+C again to exit.{Style.RESET_ALL}")
        return

async def process_accounts_batch(tokens_batch, proxies, completed_tasks, config):
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        
        for i, token in enumerate(tokens_batch):
            
            proxy = None
            if proxies and config.get("use_proxies", True):
                proxy_index = i % len(proxies)
                proxy = proxies[proxy_index]
                proxy_display = proxy.replace(":", "****:", 1) if ":" in proxy else proxy
                logger.info(f"{SYMBOLS['info']} {Fore.WHITE}Account {i+1}: Using proxy: {proxy_display}{Style.RESET_ALL}")
            
            
            tasks.append(process_account(session, token, proxy, completed_tasks, config))
        
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        
        for result in results:
            if isinstance(result, dict):  
                for email, data in result.items():
                    if email in completed_tasks:
                        
                        completed_tasks[email]["tasks"].update(data.get("tasks", {}))
                        
                        completed_tasks[email]["checkInDays"].update(data.get("checkInDays", {}))
                    else:
                        completed_tasks[email] = data
        
        return completed_tasks

async def main():
    
    print_banner()
    
    
    global logger
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger("WalmeBot")
    
    
    config = await load_or_create_config()
    
    
    setup_logging(config)
    
    
    tokens = await load_tokens()
    if not tokens:
        logger.error(f"{SYMBOLS['error']} {Fore.RED}No valid tokens found. Exiting.{Style.RESET_ALL}")
        return
        
    proxies = await load_proxies(config.get("use_proxies", True))
    completed_tasks = await load_completed_tasks()
    
    while True:
        start_time = datetime.now()
        logger.info(f"{SYMBOLS['rocket']} {Fore.CYAN}Starting new run at {start_time.strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
        logger.info(f"{Fore.CYAN}{'─' * 75}{Style.RESET_ALL}")
        
        
        max_concurrency = config.get("max_concurrency", 3)
        batch_size = max(1, min(max_concurrency, len(tokens)))
        
        
        for i in range(0, len(tokens), batch_size):
            batch = tokens[i:i+batch_size]
            logger.info(f"{SYMBOLS['processing']} {Fore.YELLOW}Processing batch {i//batch_size + 1}/{(len(tokens)+batch_size-1)//batch_size} ({len(batch)} accounts){Style.RESET_ALL}")
            
            
            completed_tasks = await process_accounts_batch(batch, proxies, completed_tasks, config)
            
            
            await save_completed_tasks(completed_tasks)
            
            
            stats = generate_stats(completed_tasks)
            save_stats(stats)
            
            
            if i + batch_size < len(tokens):
                delay = random.uniform(
                    config.get("delay_between_accounts", {}).get("min", 2.0),
                    config.get("delay_between_accounts", {}).get("max", 5.0)
                )
                logger.info(f"{SYMBOLS['time']} {Fore.BLUE}Waiting {delay:.2f}s before next batch...{Style.RESET_ALL}")
                await asyncio.sleep(delay)
        
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"{SYMBOLS['chart']} {Fore.GREEN}Run completed in {duration:.2f} seconds{Style.RESET_ALL}")
        logger.info(f"{SYMBOLS['chart']} {Fore.GREEN}Processed {len(tokens)} accounts, completed {stats['total_tasks_completed']} tasks, {stats['total_daily_checkins']} daily check-ins{Style.RESET_ALL}")
        
        
        await save_completed_tasks(completed_tasks)
        
        
        next_run_time = datetime.now() + timedelta(hours=config.get("run_interval_hours", 24))
        logger.info(f"{SYMBOLS['time']} {Fore.BLUE}Next run scheduled for {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
        
        
        display_countdown(next_run_time, config)

if __name__ == "__main__":
    try:
        
        logging.basicConfig(level=logging.INFO, format='%(message)s')
        logger = logging.getLogger("WalmeBot")
        
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{SYMBOLS['info']} {Fore.YELLOW}Bot stopped by user.{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{SYMBOLS['error']} {Fore.RED}Unexpected error: {str(e)}{Style.RESET_ALL}")