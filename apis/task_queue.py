"""任务队列管理API"""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from core.auth import get_current_user_or_ak
from core.queue.queue import TaskQueue
from core.task.task import TaskScheduler
from .base import success_response, error_response
from core.log import logger

router = APIRouter(prefix="/task-queue", tags=["任务队列"])

@router.get("/status", summary="获取任务队列状态")
async def get_queue_status(
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    获取任务队列的详细状态信息
    
    返回:
        - tag: 队列标签
        - is_running: 是否运行中
        - pending_count: 待执行任务数
        - pending_tasks: 待执行任务列表
        - current_task: 当前执行的任务
        - history_count: 历史记录总数
        - recent_history: 最近执行记录
    """
    try:
        status = TaskQueue.get_detailed_status()
        logger.info(f"Queue status: {status}")
        return success_response(data=status)
    except Exception as e:
        logger.error(f"Get queue status error: {str(e)}")
        return error_response(code=500, message=str(e))

@router.get("/history", summary="获取任务执行历史")
async def get_queue_history(
    limit: int = Query(20, ge=1, le=100, description="返回记录数量"),
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    获取任务执行历史记录
    
    参数:
        limit: 返回记录数量，默认20条
    """
    try:
        status = TaskQueue.get_detailed_status()
        history = status.get('recent_history', [])[:limit]
        return success_response(data={
            'history': history,
            'total': status.get('history_count', 0)
        })
    except Exception as e:
        return error_response(code=500, message=str(e))

@router.post("/clear", summary="清空任务队列")
async def clear_queue(
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    清空任务队列中的所有待执行任务
    
    注意: 正在执行的任务不会被中断
    """
    try:
        TaskQueue.clear_queue()
        return success_response(message="队列已清空")
    except Exception as e:
        return error_response(code=500, message=str(e))

@router.post("/history/clear", summary="清空任务历史")
async def clear_history(
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    清空任务执行历史记录
    """
    try:
        TaskQueue.clear_history()
        return success_response(message="任务历史已清空")
    except Exception as e:
        return error_response(code=500, message=str(e))

@router.get("/scheduler/status", summary="获取调度器状态")
async def get_scheduler_status(
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    获取定时任务调度器的状态信息
    
    返回:
        - running: 调度器是否运行中
        - job_count: 定时任务数量
        - next_run_times: 各任务下次执行时间
    """
    try:
        # 从 jobs.mps 导入调度器实例
        from jobs.mps import scheduler
        status = scheduler.get_scheduler_status()
        logger.info(f"Scheduler status: {status}")
        return success_response(data=status)
    except ImportError as e:
        logger.error(f"Import scheduler error: {str(e)}")
        return success_response(data={
            'running': False,
            'job_count': 0,
            'next_run_times': []
        })
    except Exception as e:
        logger.error(f"Get scheduler status error: {str(e)}")
        return error_response(code=500, message=str(e))

@router.get("/scheduler/jobs", summary="获取定时任务列表")
async def get_scheduler_jobs(
    current_user: dict = Depends(get_current_user_or_ak)
):
    """
    获取所有定时任务的详细信息
    """
    try:
        from jobs.mps import scheduler
        job_ids = scheduler.get_job_ids()
        jobs = []
        for job_id in job_ids:
            try:
                details = scheduler.get_job_details(job_id)
                jobs.append(details)
            except Exception as job_error:
                logger.warning(f"Get job {job_id} details error: {str(job_error)}")
                jobs.append({'id': job_id, 'error': '获取详情失败'})
        logger.info(f"Scheduler jobs: {len(jobs)} jobs")
        return success_response(data={
            'jobs': jobs,
            'total': len(jobs)
        })
    except ImportError as e:
        logger.error(f"Import scheduler error: {str(e)}")
        return success_response(data={
            'jobs': [],
            'total': 0
        })
    except Exception as e:
        logger.error(f"Get scheduler jobs error: {str(e)}")
        return error_response(code=500, message=str(e))
