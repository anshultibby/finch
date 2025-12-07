import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { Resource, ToolCallStatus } from '@/lib/api';
import ToolCallGroup from './ToolCallGroup';

// Dynamic import for Plotly (client-side only)
let Plot: any = null;
if (typeof window !== 'undefined') {
  import('react-plotly.js').then((module) => {
    Plot = module.default;
  });
}

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  resources?: Resource[];
  toolCalls?: ToolCallStatus[];  // Tool calls that happened before this message
  onFileClick?: (filename: string, chatId: string) => void;
  chatId?: string;
}

export default function ChatMessage({ role, content, timestamp, resources, toolCalls, onFileClick, chatId }: ChatMessageProps) {
  const isUser = role === 'user';
  const [plotLoaded, setPlotLoaded] = useState(false);
  
  // Check for plot resources
  const plotResources = resources?.filter(r => r.resource_type === 'plot') || [];
  
  // Check for file resources
  const fileResources = resources?.filter(r => r.resource_type === 'file') || [];
  
  useEffect(() => {
    // Wait for Plotly to load
    if (plotResources.length > 0 && typeof window !== 'undefined') {
      const checkPlot = setInterval(() => {
        if (Plot) {
          setPlotLoaded(true);
          clearInterval(checkPlot);
        }
      }, 100);
      return () => clearInterval(checkPlot);
    }
  }, [plotResources.length]);
  
  // Parse content for plot references like [plot:title] or [chart:title], and file references like [file:filename]
  const renderContentWithPlots = () => {
    // Check if content has plot markers or file markers
    const hasPlotMarkers = /\[(?:plot|chart):[^\]]+\]/gi.test(content);
    const hasFileMarkers = /\[file:[^\]]+\]/gi.test(content);
    
    if (!hasPlotMarkers && !hasFileMarkers) {
      // No special markers, render as normal markdown
      return (
        <ReactMarkdown
          remarkPlugins={[remarkGfm, [remarkMath, { singleDollarTextMath: false }]]}
          rehypePlugins={[rehypeKatex]}
        >
          {content}
        </ReactMarkdown>
      );
    }
    
    // Split content by plot markers and file markers
    const parts = content.split(/(\[(?:plot|chart|file):[^\]]+\])/gi);
    const elements: (JSX.Element | string)[] = [];
    
    parts.forEach((part, idx) => {
      const plotMatch = part.match(/\[(?:plot|chart):([^\]]+)\]/i);
      const fileMatch = part.match(/\[file:([^\]]+)\]/i);
      
      if (fileMatch) {
        // This is a file reference
        const filename = fileMatch[1].trim();
        const fileResource = fileResources.find(f => 
          f.data?.filename === filename
        );
        
        if (fileResource && onFileClick && chatId) {
          // Render as clickable link with file icon
          elements.push(
            <button
              key={`file-${idx}`}
              onClick={() => onFileClick(filename, chatId)}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 mx-1 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg text-blue-700 font-medium text-sm transition-all hover:shadow-sm"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {filename}
            </button>
          );
        } else {
          // File not found or no click handler, render as text
          elements.push(
            <span key={`file-notfound-${idx}`} className="inline-flex items-center gap-1 mx-1 text-gray-500 text-sm italic">
              📄 {filename}
            </span>
          );
        }
      } else if (plotMatch) {
        // This is a plot reference
        const plotTitle = plotMatch[1].trim();
        const plotResource = resources?.find(r => 
          r.resource_type === 'plot' && 
          r.title.toLowerCase().includes(plotTitle.toLowerCase())
        );
        
        if (plotResource && plotLoaded && Plot && plotResource.data.plotly_json) {
          try {
            const plotlyData = JSON.parse(plotResource.data.plotly_json);
            elements.push(
              <div key={`plot-${idx}`} className="not-prose my-4 bg-white rounded-xl shadow-md overflow-hidden border border-gray-200">
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-4 py-2 border-b border-gray-200">
                  <h4 className="text-sm font-semibold text-gray-900">{plotResource.title}</h4>
                </div>
                <div className="p-4">
                  <Plot
                    data={plotlyData.data}
                    layout={{
                      ...plotlyData.layout,
                      autosize: true,
                      margin: { l: 50, r: 30, t: 50, b: 50 }
                    }}
                    config={{
                      responsive: true,
                      displayModeBar: true,
                      displaylogo: false,
                      modeBarButtonsToRemove: ['lasso2d', 'select2d']
                    }}
                    style={{ width: '100%', height: '400px' }}
                    useResizeHandler={true}
                  />
                </div>
              </div>
            );
          } catch (error) {
            elements.push(
              <div key={`plot-error-${idx}`} className="not-prose my-4 text-center py-4 text-red-500 bg-red-50 rounded-lg">
                Error rendering chart: {String(error)}
              </div>
            );
          }
        } else {
          // Plot reference but not loaded yet
          elements.push(
            <div key={`plot-loading-${idx}`} className="not-prose my-4 flex items-center justify-center py-8 bg-gray-50 rounded-lg">
              <div className="text-gray-500">Loading chart...</div>
            </div>
          );
        }
      } else if (part.trim()) {
        // This is regular markdown content - render inline
        elements.push(
          <ReactMarkdown
            key={`content-${idx}`}
            remarkPlugins={[remarkGfm, [remarkMath, { singleDollarTextMath: false }]]}
            rehypePlugins={[rehypeKatex]}
          >
            {part}
          </ReactMarkdown>
        );
      }
    });
    
    return <>{elements}</>;
  };
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-[80%] ${isUser ? 'order-2' : 'order-1'}`}>
        {isUser ? (
          /* User messages: keep bubble style */
          <div className="rounded-2xl px-4 py-3 bg-primary-600 text-white rounded-br-none shadow-sm">
            <p className="text-sm whitespace-pre-wrap break-words">{content}</p>
          </div>
        ) : (
          /* AI messages: tool calls first, then content */
          <>
            {/* Tool Calls Group - shown before the message */}
            {toolCalls && toolCalls.length > 0 && (
              <ToolCallGroup toolCalls={toolCalls} timestamp={timestamp} />
            )}
            
            {/* Message Content */}
          <div className="px-3 py-2">
            <div className="prose prose-sm prose-slate max-w-none
              prose-headings:font-semibold prose-headings:text-gray-900
              prose-h1:text-xl prose-h2:text-lg prose-h3:text-base
              prose-p:text-[15px] prose-p:text-gray-900 prose-p:leading-relaxed prose-p:my-3 prose-p:ml-0
              prose-a:text-blue-600 prose-a:no-underline hover:prose-a:underline
              prose-strong:text-gray-900 prose-strong:font-semibold
              prose-code:text-sm prose-code:bg-gray-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-gray-800 prose-code:before:content-none prose-code:after:content-none
              prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-pre:rounded-lg prose-pre:p-4 prose-pre:my-3
              prose-ul:my-3 prose-ul:ml-4 prose-ol:my-3 prose-ol:ml-4 prose-li:my-1 prose-li:text-[15px] prose-li:text-gray-900
              prose-table:text-sm prose-table:my-3
              prose-th:bg-gray-100 prose-th:font-semibold prose-th:p-2
              prose-td:p-2 prose-td:border prose-td:border-gray-200
              prose-blockquote:border-l-4 prose-blockquote:border-gray-300 prose-blockquote:pl-4 prose-blockquote:italic prose-blockquote:text-gray-700
              prose-img:rounded-lg prose-img:shadow-md">
              {renderContentWithPlots()}
            </div>
          </div>
          </>
        )}
      </div>
    </div>
  );
}

