import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import {
  ChartBarIcon,
  DocumentTextIcon,
  CalendarIcon,
  UserGroupIcon,
  UserCircleIcon,
  CogIcon,
  ClipboardListIcon,
  TrendingUpIcon,
  PencilIcon,
  ArrowPathIcon,
  ExclamationCircleIcon
} from '@heroicons/react/24/outline';

interface DashboardView {
  id: string;
  title: string;
  icon: any;
  description: string;
  color: string;
}

const dashboardViews: DashboardView[] = [
  {
    id: 'knowledge',
    title: 'Knowledge',
    icon: DocumentTextIcon,
    description: 'Document insights and knowledge management',
    color: 'bg-blue-500'
  },
  {
    id: 'processes',
    title: 'Processes',
    icon: CogIcon,
    description: 'Workflow optimization and automation',
    color: 'bg-green-500'
  },
  {
    id: 'calendar',
    title: 'Calendar',
    icon: CalendarIcon,
    description: 'Schedule analytics and time management',
    color: 'bg-purple-500'
  },
  {
    id: 'relationships',
    title: 'Relationships',
    icon: UserGroupIcon,
    description: 'Network analysis and communication patterns',
    color: 'bg-pink-500'
  },
  {
    id: 'persona',
    title: 'Persona',
    icon: UserCircleIcon,
    description: 'Behavioral patterns and personality insights',
    color: 'bg-indigo-500'
  },
  {
    id: 'tools',
    title: 'Tools',
    icon: CogIcon,
    description: 'Integration status and API health',
    color: 'bg-yellow-500'
  },
  {
    id: 'tasks',
    title: 'Tasks',
    icon: ClipboardListIcon,
    description: 'Task management and productivity',
    color: 'bg-red-500'
  },
  {
    id: 'growth',
    title: 'Growth',
    icon: TrendingUpIcon,
    description: 'Personal development and learning',
    color: 'bg-teal-500'
  },
  {
    id: 'content',
    title: 'Content',
    icon: PencilIcon,
    description: 'Content creation and writing analytics',
    color: 'bg-orange-500'
  }
];

export default function Dashboard() {
  const router = useRouter();
  const [selectedView, setSelectedView] = useState<string>('knowledge');
  const [viewData, setViewData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<any>(null);
  const [taskStatus, setTaskStatus] = useState<any[]>([]);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }
    
    // Load initial view
    loadDashboardView(selectedView);
    
    // Load task status
    loadTaskStatus();
    
    // Check for Microsoft auth
    checkMicrosoftAuth();
  }, []);

  const loadDashboardView = async (view: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/dashboard/${view}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`Failed to load ${view} view`);
      }
      
      const data = await response.json();
      setViewData(data);
      setSelectedView(view);
    } catch (err: any) {
      setError(err.message);
      console.error('Dashboard error:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadTaskStatus = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/tasks?limit=5', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const tasks = await response.json();
        setTaskStatus(tasks);
      }
    } catch (err) {
      console.error('Failed to load tasks:', err);
    }
  };

  const checkMicrosoftAuth = async () => {
    try {
      const response = await fetch('/api/auth/microsoft');
      if (response.ok) {
        const data = await response.json();
        if (data.auth_url) {
          // Microsoft auth is available
          console.log('Microsoft auth available');
        }
      }
    } catch (err) {
      console.error('Microsoft auth check failed:', err);
    }
  };

  const handleSync = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/twin/demo-twin/sync', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          sources: ['emails', 'calendar', 'files', 'teams']
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        setSyncStatus(result);
        
        // Reload current view after sync
        setTimeout(() => {
          loadDashboardView(selectedView);
          loadTaskStatus();
        }, 2000);
      }
    } catch (err) {
      console.error('Sync failed:', err);
    }
  };

  const handleMicrosoftLogin = () => {
    window.location.href = '/api/auth/microsoft';
  };

  const renderViewContent = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        </div>
      );
    }

    if (error) {
      return (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <ExclamationCircleIcon className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          </div>
        </div>
      );
    }

    if (!viewData) {
      return (
        <div className="text-center text-gray-500 py-8">
          No data available. Try syncing your data sources.
        </div>
      );
    }

    // Render based on selected view
    switch (selectedView) {
      case 'knowledge':
        return renderKnowledgeView();
      case 'processes':
        return renderProcessesView();
      case 'calendar':
        return renderCalendarView();
      case 'relationships':
        return renderRelationshipsView();
      case 'persona':
        return renderPersonaView();
      case 'tools':
        return renderToolsView();
      case 'tasks':
        return renderTasksView();
      case 'growth':
        return renderGrowthView();
      case 'content':
        return renderContentView();
      default:
        return <div>View not implemented</div>;
    }
  };

  const renderKnowledgeView = () => {
    const metrics = viewData?.metrics || {};
    const categories = viewData?.categories || {};
    const topics = viewData?.topics || [];
    
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <MetricCard title="Total Documents" value={metrics.total_documents || 0} />
          <MetricCard title="Data Sources" value={metrics.sources || 0} />
          <MetricCard title="Topics" value={metrics.topics_identified || 0} />
          <MetricCard title="Growth Rate" value={`${metrics.growth_rate || 0}%`} />
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">Knowledge Categories</h3>
          <div className="space-y-2">
            {Object.entries(categories).map(([category, count]) => (
              <div key={category} className="flex justify-between items-center">
                <span className="text-sm text-gray-600">{category}</span>
                <span className="text-sm font-medium">{count as number}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">Top Topics</h3>
          <div className="flex flex-wrap gap-2">
            {topics.map((topic: string, idx: number) => (
              <span key={idx} className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                {topic}
              </span>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderProcessesView = () => {
    const metrics = viewData?.metrics || {};
    const processes = viewData?.process_breakdown || {};
    const opportunities = viewData?.automation_opportunities || [];
    
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <MetricCard title="Total Processes" value={metrics.total_processes || 0} />
          <MetricCard title="Automated" value={metrics.automated || 0} />
          <MetricCard title="Manual" value={metrics.manual || 0} />
          <MetricCard title="Efficiency" value={`${metrics.efficiency_score || 0}%`} />
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">Process Breakdown</h3>
          <div className="space-y-3">
            {Object.entries(processes).map(([process, data]: [string, any]) => (
              <div key={process} className="flex justify-between items-center">
                <span className="text-sm text-gray-600">{process}</span>
                <div className="text-right">
                  <span className="text-sm font-medium">{data.count}</span>
                  <span className="text-xs text-gray-500 ml-2">({data.percentage?.toFixed(1)}%)</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">Automation Opportunities</h3>
          <div className="space-y-3">
            {opportunities.map((opp: any, idx: number) => (
              <div key={idx} className="border-l-4 border-green-500 pl-4">
                <div className="flex justify-between">
                  <span className="font-medium">{opp.type}</span>
                  <span className="text-sm text-green-600">{opp.potential_savings}</span>
                </div>
                <div className="text-sm text-gray-600">
                  Impact: {opp.impact} | Difficulty: {opp.difficulty}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderCalendarView = () => {
    const metrics = viewData?.metrics || {};
    const meetingTypes = viewData?.meeting_types || {};
    const patterns = viewData?.patterns || {};
    
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <MetricCard title="Total Meetings" value={metrics.total_meetings || 0} />
          <MetricCard title="Avg Per Day" value={metrics.avg_per_day || 0} />
          <MetricCard title="Busiest Day" value={metrics.busiest_day || 'N/A'} />
          <MetricCard title="Meeting Load" value={metrics.meeting_load || 'Low'} />
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">Meeting Types</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(meetingTypes).map(([type, count]) => (
              <div key={type} className="text-center">
                <div className="text-2xl font-bold text-purple-600">{count as number}</div>
                <div className="text-sm text-gray-600">{type}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">Calendar Patterns</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-xl font-bold">{patterns.back_to_back || 0}</div>
              <div className="text-sm text-gray-600">Back-to-back</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold">{patterns.recurring || 0}</div>
              <div className="text-sm text-gray-600">Recurring</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold">{patterns.long_meetings || 0}</div>
              <div className="text-sm text-gray-600">Long Meetings</div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderRelationshipsView = () => {
    const metrics = viewData?.metrics || {};
    const topContacts = viewData?.top_contacts || [];
    const networkHealth = viewData?.network_health || {};
    
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <MetricCard title="Total Contacts" value={metrics.total_contacts || 0} />
          <MetricCard title="Interactions" value={metrics.total_interactions || 0} />
          <MetricCard title="Avg Interactions" value={metrics.avg_interactions || 0} />
          <MetricCard title="Active Relations" value={metrics.active_relationships || 0} />
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">Top Contacts</h3>
          <div className="space-y-3">
            {topContacts.slice(0, 5).map((contact: any, idx: number) => (
              <div key={idx} className="flex justify-between items-center">
                <div>
                  <div className="font-medium">{contact.email}</div>
                  <div className="text-sm text-gray-600">via {contact.primary_channel}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-medium">{contact.interactions} interactions</div>
                  <div className="text-xs text-gray-500">Score: {contact.relationship_score}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">Network Health</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-xl font-bold text-pink-600">{networkHealth.diversity_score || 0}</div>
              <div className="text-sm text-gray-600">Diversity</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-pink-600">{networkHealth.engagement_score || 0}</div>
              <div className="text-sm text-gray-600">Engagement</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-pink-600">{networkHealth.growth_rate || 0}%</div>
              <div className="text-sm text-gray-600">Growth Rate</div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderPersonaView = () => {
    const twinInfo = viewData?.twin_info || {};
    const behavioralDimensions = viewData?.behavioral_dimensions || {};
    const personalityTraits = viewData?.personality_traits || {};
    
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">Digital Twin Profile</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-sm text-gray-600">Name:</span>
              <p className="font-medium">{twinInfo.name || 'Digital Twin'}</p>
            </div>
            <div>
              <span className="text-sm text-gray-600">Capability:</span>
              <p className="font-medium">{twinInfo.capability_level || 'L1'}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">Behavioral Dimensions (Fourth Ontology)</h3>
          <div className="space-y-3">
            {Object.entries(behavioralDimensions).map(([dimension, score]) => (
              <div key={dimension}>
                <div className="flex justify-between mb-1">
                  <span className="text-sm font-medium">{dimension}</span>
                  <span className="text-sm">{score as number}/100</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-indigo-600 h-2 rounded-full" 
                    style={{ width: `${score}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">Personality Traits</h3>
          <div className="space-y-3">
            {Object.entries(personalityTraits).map(([trait, score]) => (
              <div key={trait}>
                <div className="flex justify-between mb-1">
                  <span className="text-sm font-medium">{trait}</span>
                  <span className="text-sm">{score as number}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-indigo-600 h-2 rounded-full" 
                    style={{ width: `${score}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderToolsView = () => {
    const connectedTools = viewData?.connected_tools || {};
    const apiHealth = viewData?.api_health || {};
    const usageStats = viewData?.usage_statistics || {};
    
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <MetricCard title="Integrations" value={usageStats.total_integrations || 0} />
          <MetricCard title="Data Points" value={usageStats.total_data_points || 0} />
          <MetricCard title="Last Sync" value="Recently" />
          <MetricCard title="Sync Frequency" value={usageStats.sync_frequency || 'Daily'} />
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">Connected Tools</h3>
          <div className="space-y-3">
            {Object.entries(connectedTools).map(([tool, data]: [string, any]) => (
              <div key={tool} className="flex justify-between items-center p-3 border rounded-lg">
                <div>
                  <div className="font-medium">{tool}</div>
                  <div className="text-sm text-gray-600">{data.data_points} data points</div>
                </div>
                <div className={`px-3 py-1 rounded-full text-sm ${
                  data.status === 'connected' 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {data.status}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">API Health</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(apiHealth).map(([api, status]) => (
              <div key={api} className="text-center">
                <div className={`text-2xl mb-2 ${
                  status === 'healthy' ? 'text-green-500' : 'text-yellow-500'
                }`}>
                  {status === 'healthy' ? '✓' : '!'}
                </div>
                <div className="text-sm text-gray-600">{api}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderTasksView = () => {
    const metrics = viewData?.metrics || {};
    const activeTasks = viewData?.active_tasks || [];
    const taskPatterns = viewData?.task_patterns || {};
    
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <MetricCard title="Total Tasks" value={metrics.total_tasks || 0} />
          <MetricCard title="High Priority" value={metrics.high_priority || 0} />
          <MetricCard title="Completion Rate" value={`${metrics.completion_rate || 0}%`} />
          <MetricCard title="Productivity" value={`${metrics.productivity_score || 0}/100`} />
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">Active Tasks</h3>
          <div className="space-y-3">
            {activeTasks.slice(0, 10).map((task: any, idx: number) => (
              <div key={idx} className="flex items-start space-x-3">
                <div className={`mt-1 w-2 h-2 rounded-full ${
                  task.priority === 'high' ? 'bg-red-500' : 'bg-yellow-500'
                }`}></div>
                <div className="flex-1">
                  <p className="text-sm">{task.description}</p>
                  <p className="text-xs text-gray-500">from {task.source}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">Background Tasks</h3>
          <div className="space-y-2">
            {taskStatus.map((task: any) => (
              <div key={task.task_id} className="flex justify-between items-center">
                <span className="text-sm">{task.type}</span>
                <span className={`px-2 py-1 text-xs rounded-full ${
                  task.status === 'success' ? 'bg-green-100 text-green-800' :
                  task.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {task.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderGrowthView = () => {
    const metrics = viewData?.metrics || {};
    const skillLevels = viewData?.skill_levels || {};
    const learningTopics = viewData?.learning_topics || [];
    
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <MetricCard title="Growth Rate" value={`${metrics.growth_rate || 0}%`} />
          <MetricCard title="Learning Velocity" value={metrics.learning_velocity || 'Low'} />
          <MetricCard title="Skills Developing" value={metrics.skills_developing || 0} />
          <MetricCard title="Knowledge Areas" value={metrics.knowledge_expansion || 0} />
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">Skill Development</h3>
          <div className="space-y-3">
            {Object.entries(skillLevels).map(([skill, level]) => (
              <div key={skill}>
                <div className="flex justify-between mb-1">
                  <span className="text-sm font-medium">{skill}</span>
                  <span className="text-sm">{level as number}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-teal-600 h-2 rounded-full" 
                    style={{ width: `${level}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">Learning Topics</h3>
          <div className="flex flex-wrap gap-2">
            {learningTopics.map((topic: string, idx: number) => (
              <span key={idx} className="px-3 py-1 bg-teal-100 text-teal-800 rounded-full text-sm">
                {topic}
              </span>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderContentView = () => {
    const metrics = viewData?.metrics || {};
    const contentTypes = viewData?.content_types || {};
    const writingPatterns = viewData?.writing_patterns || {};
    
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <MetricCard title="Total Content" value={metrics.total_content || 0} />
          <MetricCard title="Total Words" value={metrics.total_words || 0} />
          <MetricCard title="Avg Length" value={`${metrics.avg_length || 0} words`} />
          <MetricCard title="Quality Score" value={`${metrics.quality_score || 0}/100`} />
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">Content Types</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {Object.entries(contentTypes).map(([type, count]) => (
              <div key={type} className="text-center">
                <div className="text-2xl font-bold text-orange-600">{count as number}</div>
                <div className="text-sm text-gray-600">{type}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium mb-4">Writing Patterns</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-sm text-gray-600">Peak Day</div>
              <div className="font-medium">{writingPatterns.peak_day || 'N/A'}</div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-600">Avg/Day</div>
              <div className="font-medium">{writingPatterns.avg_per_day || 0}</div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-600">Consistency</div>
              <div className="font-medium">{writingPatterns.consistency || 'Low'}</div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">BDT Platform Dashboard</h1>
              <p className="text-sm text-gray-600 mt-1">Behavioral Digital Twin Analytics</p>
            </div>
            <div className="flex space-x-4">
              <button
                onClick={handleMicrosoftLogin}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Connect Microsoft
              </button>
              <button
                onClick={handleSync}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center"
              >
                <ArrowPathIcon className="h-5 w-5 mr-2" />
                Sync Data
              </button>
            </div>
          </div>

          {syncStatus && (
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">
                Sync {syncStatus.status}: Task ID {syncStatus.task_id}
              </p>
            </div>
          )}
        </div>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar - View Selection */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-sm p-4">
              <h2 className="text-sm font-medium text-gray-700 mb-3">Views</h2>
              <nav className="space-y-1">
                {dashboardViews.map((view) => (
                  <button
                    key={view.id}
                    onClick={() => loadDashboardView(view.id)}
                    className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-lg transition ${
                      selectedView === view.id
                        ? 'bg-indigo-100 text-indigo-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    <view.icon className="h-5 w-5 mr-3" />
                    {view.title}
                  </button>
                ))}
              </nav>
            </div>
          </div>

          {/* Main Content Area */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="mb-6">
                <h2 className="text-lg font-medium text-gray-900">
                  {dashboardViews.find(v => v.id === selectedView)?.title}
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  {dashboardViews.find(v => v.id === selectedView)?.description}
                </p>
              </div>

              {renderViewContent()}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Metric Card Component
function MetricCard({ title, value }: { title: string; value: any }) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <p className="text-sm text-gray-600">{title}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
    </div>
  );
}