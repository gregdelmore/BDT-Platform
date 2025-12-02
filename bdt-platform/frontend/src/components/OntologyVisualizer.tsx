import React, { useEffect, useRef, useState } from 'react';
import { Radar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
} from 'chart.js';

ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
);

interface OntologyDimensions {
  decisions: number;
  power: number;
  fear: number;
  reward: number;
  meaning: number;
}

interface OntologyVisualizerProps {
  personaId: string;
  dimensions: OntologyDimensions;
  onDimensionChange?: (dimension: string, value: number) => void;
  isEditable?: boolean;
  showComparison?: boolean;
  comparisonDimensions?: OntologyDimensions;
}

const OntologyVisualizer: React.FC<OntologyVisualizerProps> = ({
  personaId,
  dimensions,
  onDimensionChange,
  isEditable = false,
  showComparison = false,
  comparisonDimensions
}) => {
  const [localDimensions, setLocalDimensions] = useState(dimensions);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    setLocalDimensions(dimensions);
  }, [dimensions]);

  const data = {
    labels: [
      'Decisions (Analysis Depth)',
      'Power (Autonomy)',
      'Fear (Risk Aversion)',
      'Reward (Motivation)',
      'Meaning (Values)'
    ],
    datasets: [
      {
        label: 'Current Profile',
        data: [
          localDimensions.decisions,
          localDimensions.power,
          localDimensions.fear,
          localDimensions.reward,
          localDimensions.meaning
        ],
        backgroundColor: 'rgba(30, 58, 138, 0.2)',
        borderColor: 'rgba(30, 58, 138, 1)',
        borderWidth: 2,
        pointBackgroundColor: 'rgba(30, 58, 138, 1)',
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: 'rgba(30, 58, 138, 1)'
      }
    ]
  };

  if (showComparison && comparisonDimensions) {
    data.datasets.push({
      label: 'Group Average',
      data: [
        comparisonDimensions.decisions,
        comparisonDimensions.power,
        comparisonDimensions.fear,
        comparisonDimensions.reward,
        comparisonDimensions.meaning
      ],
      backgroundColor: 'rgba(16, 185, 129, 0.2)',
      borderColor: 'rgba(16, 185, 129, 1)',
      borderWidth: 2,
      pointBackgroundColor: 'rgba(16, 185, 129, 1)',
      pointBorderColor: '#fff',
      pointHoverBackgroundColor: '#fff',
      pointHoverBorderColor: 'rgba(16, 185, 129, 1)'
    });
  }

  const options = {
    scales: {
      r: {
        angleLines: {
          display: true,
          color: 'rgba(0, 0, 0, 0.1)'
        },
        suggestedMin: 0,
        suggestedMax: 100,
        ticks: {
          stepSize: 20
        }
      }
    },
    plugins: {
      legend: {
        position: 'top' as const
      },
      tooltip: {
        callbacks: {
          label: (context: any) => {
            return `${context.dataset.label}: ${context.parsed.r}`;
          }
        }
      }
    },
    maintainAspectRatio: true
  };

  const handleSliderChange = (dimension: string, value: number) => {
    setLocalDimensions(prev => ({
      ...prev,
      [dimension]: value
    }));
    
    if (onDimensionChange) {
      onDimensionChange(dimension, value);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="mb-4">
        <h2 className="text-2xl font-bold text-gray-900">Fourth Ontology Profile</h2>
        <p className="text-gray-600">Behavioral dimension mapping for {personaId}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Radar Chart */}
        <div className="flex items-center justify-center">
          <div className="w-full max-w-md">
            <Radar data={data} options={options} />
          </div>
        </div>

        {/* Dimension Controls */}
        <div className="space-y-4">
          {Object.entries(localDimensions).map(([dimension, value]) => (
            <div key={dimension} className="space-y-2">
              <div className="flex justify-between items-center">
                <label className="text-sm font-medium text-gray-700 capitalize">
                  {dimension}
                </label>
                <span className="text-sm text-gray-500">{value}/100</span>
              </div>
              
              <div className="relative">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={value}
                  onChange={(e) => handleSliderChange(dimension, parseInt(e.target.value))}
                  disabled={!isEditable}
                  className={`w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer 
                    ${isEditable ? 'hover:bg-gray-300' : 'opacity-50 cursor-not-allowed'}`}
                />
                
                {/* Value indicator */}
                <div 
                  className="absolute -top-8 transform -translate-x-1/2 bg-gray-900 text-white text-xs rounded px-2 py-1"
                  style={{ left: `${value}%` }}
                >
                  {value}
                </div>
              </div>
              
              {/* Dimension description */}
              <p className="text-xs text-gray-500">
                {getDimensionDescription(dimension, value)}
              </p>
            </div>
          ))}

          {isEditable && (
            <div className="pt-4 border-t">
              <button
                onClick={() => setLocalDimensions(dimensions)}
                className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition"
              >
                Reset to Original
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Behavioral Insights */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg">
        <h3 className="text-lg font-semibold text-blue-900 mb-2">Behavioral Insights</h3>
        <div className="space-y-2 text-sm text-blue-800">
          {generateInsights(localDimensions).map((insight, index) => (
            <div key={index} className="flex items-start">
              <span className="text-blue-500 mr-2">•</span>
              <span>{insight}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Helper functions
function getDimensionDescription(dimension: string, value: number): string {
  const descriptions: Record<string, Record<string, string>> = {
    decisions: {
      low: "Makes quick decisions with minimal analysis",
      medium: "Balances speed and thoroughness in decision-making",
      high: "Requires extensive data and analysis before decisions"
    },
    power: {
      low: "Prefers delegation and collaborative decision-making",
      medium: "Comfortable with moderate autonomy",
      high: "Strongly prefers independent action and control"
    },
    fear: {
      low: "High risk tolerance, comfortable with uncertainty",
      medium: "Balanced approach to risk management",
      high: "Highly risk-averse, prioritizes safety and stability"
    },
    reward: {
      low: "Motivated by intrinsic factors and purpose",
      medium: "Balanced between intrinsic and extrinsic motivation",
      high: "Strongly driven by measurable outcomes and recognition"
    },
    meaning: {
      low: "Task-focused, prioritizes efficiency",
      medium: "Balances task completion with value alignment",
      high: "Strongly values alignment with mission and purpose"
    }
  };

  const level = value < 33 ? 'low' : value < 67 ? 'medium' : 'high';
  return descriptions[dimension]?.[level] || '';
}

function generateInsights(dimensions: OntologyDimensions): string[] {
  const insights: string[] = [];

  // Decision-Power combination
  if (dimensions.decisions > 70 && dimensions.power < 40) {
    insights.push("Prefers thorough analysis but seeks approval before acting");
  } else if (dimensions.decisions < 30 && dimensions.power > 60) {
    insights.push("Makes quick, autonomous decisions with confidence");
  }

  // Fear-Reward combination
  if (dimensions.fear > 70 && dimensions.reward > 70) {
    insights.push("Cautious approach with focus on guaranteed outcomes");
  } else if (dimensions.fear < 30 && dimensions.reward < 30) {
    insights.push("Risk-tolerant with intrinsic motivation");
  }

  // Meaning alignment
  if (dimensions.meaning > 80) {
    insights.push("Decisions heavily influenced by organizational values");
  } else if (dimensions.meaning < 20) {
    insights.push("Pragmatic focus on task completion over ideals");
  }

  // Autonomy patterns
  if (dimensions.power > 80) {
    insights.push("Strong preference for independent operation");
  } else if (dimensions.power < 20) {
    insights.push("Consistently seeks collaborative input");
  }

  return insights;
}

export default OntologyVisualizer;