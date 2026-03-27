import http from './http';

export interface TaskRecord {
  task_name: string;
  start_time: string;
  end_time: string | null;
  duration: number | null;
  status: 'running' | 'completed' | 'failed';
  error: string | null;
}

export interface PendingTask {
  task_name: string;
  args: string;
  kwargs: string;
  add_time: string;
}

export interface CurrentTask {
  task_name: string;
  start_time: string;
  status: string;
}

export interface QueueStatus {
  tag: string;
  is_running: boolean;
  pending_count: number;
  pending_tasks: PendingTask[];
  current_task: CurrentTask | null;
  history_count: number;
  recent_history: TaskRecord[];
}

export interface SchedulerJob {
  id: string;
  name: string;
  trigger: string;
  next_run_time: string | null;
  last_run_time: string | null;
}

export interface SchedulerStatus {
  running: boolean;
  job_count: number;
  next_run_times: [string, string | null][];
}

export const getQueueStatus = async (): Promise<QueueStatus> => {
  try {
    const response = await http.get('/wx/task-queue/status');
    console.log('Queue status response:', response);
    // http 拦截器已经解包了 response.data.data
    // response 可能是 data 本身
    const data = response as any;
    if (data && typeof data === 'object') {
      return {
        tag: data.tag || '',
        is_running: data.is_running || false,
        pending_count: data.pending_count || 0,
        pending_tasks: data.pending_tasks || [],
        current_task: data.current_task || null,
        history_count: data.history_count || 0,
        recent_history: data.recent_history || [],
      };
    }
    return {
      tag: '',
      is_running: false,
      pending_count: 0,
      pending_tasks: [],
      current_task: null,
      history_count: 0,
      recent_history: [],
    };
  } catch (error) {
    console.error('Get queue status error:', error);
    throw error;
  }
};

export const getQueueHistory = async (limit: number = 20): Promise<{ history: TaskRecord[]; total: number }> => {
  try {
    const response = await http.get('/wx/task-queue/history', { params: { limit } });
    const data = response as any;
    return {
      history: data?.history || [],
      total: data?.total || 0,
    };
  } catch (error) {
    console.error('Get queue history error:', error);
    throw error;
  }
};

export const clearQueue = async (): Promise<void> => {
  await http.post('/wx/task-queue/clear');
};

export const clearHistory = async (): Promise<void> => {
  await http.post('/wx/task-queue/history/clear');
};

export const getSchedulerStatus = async (): Promise<SchedulerStatus> => {
  try {
    const response = await http.get('/wx/task-queue/scheduler/status');
    const data = response as any;
    return {
      running: data?.running || false,
      job_count: data?.job_count || 0,
      next_run_times: data?.next_run_times || [],
    };
  } catch (error) {
    console.error('Get scheduler status error:', error);
    throw error;
  }
};

export const getSchedulerJobs = async (): Promise<{ jobs: SchedulerJob[]; total: number }> => {
  try {
    const response = await http.get('/wx/task-queue/scheduler/jobs');
    const data = response as any;
    return {
      jobs: data?.jobs || [],
      total: data?.total || 0,
    };
  } catch (error) {
    console.error('Get scheduler jobs error:', error);
    throw error;
  }
};
