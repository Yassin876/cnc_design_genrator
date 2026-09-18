import React, { useState } from 'react';
import { 
  Folder, Layers, Box, Component as ComponentIcon, 
  Circle, Flame, Eye, EyeOff, Edit3, Trash2, Maximize2,
  ChevronDown, ChevronRight, Check, X, ShieldAlert, Sliders
} from 'lucide-react';


import { useWorkspaceStore } from '../../../app/store/useWorkspaceStore';
import { TreeNode } from '../../../types';

interface TreeNodeItemProps {
  node: TreeNode;
  level: number;
}

export const TreeNodeItem: React.FC<TreeNodeItemProps> = ({ node, level }) => {
  const { 
    selectedNodeId, selectTreeNode, toggleNodeVisibility, 
    renameTreeNode, isolateTreeNode, deleteTreeNode, toggleNodeExpand 
  } = useWorkspaceStore();

  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(node.name);

  const isSelected = selectedNodeId === node.id;
  const hasChildren = node.children && node.children.length > 0;

  const getIcon = (type: TreeNode['type']) => {
    switch (type) {
      case 'Project':
        return <Folder className="w-3.5 h-3.5 text-amber-400" />;
      case 'Assembly':
        return <Layers className="w-3.5 h-3.5 text-violet-400" />;
      case 'Body':
        return <Box className="w-3.5 h-3.5 text-cyan-400" />;
      case 'Component':
        return <ComponentIcon className="w-3.5 h-3.5 text-blue-400" />;
      case 'Hole':
        return <Circle className="w-3.5 h-3.5 text-red-400" />;
      case 'Fillet':
        return <Flame className="w-3.5 h-3.5 text-emerald-400" />;
      case 'Flange':
        return <Sliders className="w-3.5 h-3.5 text-yellow-400" />;
      case 'Surface':
        return <Maximize2 className="w-3.5 h-3.5 text-pink-400" />;
      default:
        return <Box className="w-3.5 h-3.5 text-cad-textMuted" />;
    }
  };

  const handleSaveRename = (e: React.FormEvent) => {
    e.preventDefault();
    if (editName.trim()) {
      renameTreeNode(node.id, editName.trim());
    }
    setIsEditing(false);
  };

  return (
    <div className="select-none font-mono text-xs">
      <div 
        className={`group flex items-center justify-between py-1.5 px-2 rounded-lg cursor-pointer transition-colors ${
          isSelected 
            ? 'bg-violet-950/70 border border-violet-700/60 text-white font-semibold' 
            : 'hover:bg-cad-surface text-cad-textMain'
        }`}
        style={{ paddingLeft: `${level * 14 + 8}px` }}
        onClick={() => selectTreeNode(node.id)}
      >
        <div className="flex items-center space-x-1.5 flex-1 min-w-0">
          {hasChildren ? (
            <button 
              onClick={(e) => {
                e.stopPropagation();
                toggleNodeExpand(node.id);
              }}
              className="p-0.5 text-cad-textMuted hover:text-white"
            >
              {node.expanded ? (
                <ChevronDown className="w-3.5 h-3.5" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5" />
              )}
            </button>
          ) : (
            <span className="w-3.5 h-3.5 inline-block" />
          )}

          <span className="shrink-0">{getIcon(node.type)}</span>

          {isEditing ? (
            <form onSubmit={handleSaveRename} className="flex items-center space-x-1 flex-1" onClick={(e) => e.stopPropagation()}>
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                autoFocus
                className="bg-cad-bg border border-violet-500 text-white text-xs px-1.5 py-0.5 rounded outline-none w-full"
              />
              <button type="submit" className="text-emerald-400 hover:text-emerald-300">
                <Check className="w-3.5 h-3.5" />
              </button>
              <button type="button" onClick={() => setIsEditing(false)} className="text-red-400 hover:text-red-300">
                <X className="w-3.5 h-3.5" />
              </button>
            </form>
          ) : (
            <span className="truncate text-xs">{node.name}</span>
          )}
        </div>

        {/* Hover / Active Action Icons */}
        <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={(e) => {
              e.stopPropagation();
              toggleNodeVisibility(node.id);
            }}
            className={`p-1 rounded hover:bg-cad-bg ${node.visible ? 'text-cad-textMuted hover:text-white' : 'text-red-400'}`}
            title={node.visible ? 'Hide Element' : 'Show Element'}
          >
            {node.visible ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsEditing(true);
            }}
            className="p-1 rounded hover:bg-cad-bg text-cad-textMuted hover:text-white"
            title="Rename Element"
          >
            <Edit3 className="w-3 h-3" />
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              isolateTreeNode(node.id);
            }}
            className="p-1 rounded hover:bg-cad-bg text-cad-textMuted hover:text-cyan-400"
            title="Isolate Element"
          >
            <Maximize2 className="w-3 h-3" />
          </button>


          {node.type !== 'Project' && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                deleteTreeNode(node.id);
              }}
              className="p-1 rounded hover:bg-cad-bg text-cad-textMuted hover:text-red-400"
              title="Delete Element"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {hasChildren && node.expanded && (
        <div className="space-y-0.5 mt-0.5">
          {node.children!.map((child) => (
            <TreeNodeItem key={child.id} node={child} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  );
};

export const ModelTree: React.FC = () => {
  const { treeNodes, setTreeNodes, selectedNodeId } = useWorkspaceStore();

  const handleAddFeature = (type: TreeNode['type']) => {
    const newNode: TreeNode = {
      id: `feat_${Date.now()}`,
      name: `New ${type}`,
      type,
      visible: true,
      properties: {}
    };

    const updateNodes = (nodes: TreeNode[]): TreeNode[] =>
      nodes.map((n) => {
        if (n.id === 'asm_main' || n.type === 'Assembly') {
          return { ...n, children: [...(n.children || []), newNode] };
        }
        if (n.children) return { ...n, children: updateNodes(n.children) };
        return n;
      });

    setTreeNodes(updateNodes(treeNodes));
  };

  return (
    <div className="flex-1 flex flex-col justify-between bg-cad-panel overflow-hidden select-none">
      
      {/* Header Actions */}
      <div className="p-3 border-b border-cad-border flex items-center justify-between">
        <span className="text-[10px] font-mono text-cad-textMuted uppercase tracking-wider">
          CAD Structure Tree
        </span>
        <div className="flex items-center space-x-1">
          <button
            onClick={() => handleAddFeature('Hole')}
            className="text-[10px] font-mono bg-cad-surface hover:bg-cad-card text-red-300 border border-cad-border px-1.5 py-0.5 rounded"
            title="Add Hole Feature"
          >
            + Hole
          </button>
          <button
            onClick={() => handleAddFeature('Fillet')}
            className="text-[10px] font-mono bg-cad-surface hover:bg-cad-card text-emerald-300 border border-cad-border px-1.5 py-0.5 rounded"
            title="Add Fillet Feature"
          >
            + Fillet
          </button>
          <button
            onClick={() => handleAddFeature('Flange')}
            className="text-[10px] font-mono bg-cad-surface hover:bg-cad-card text-amber-300 border border-cad-border px-1.5 py-0.5 rounded"
            title="Add Flange Feature"
          >
            + Flange
          </button>
        </div>
      </div>

      {/* Tree Content */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {treeNodes.map((node) => (
          <TreeNodeItem key={node.id} node={node} level={0} />
        ))}
      </div>

      {/* Selection Summary Footer */}
      <div className="p-3 border-t border-cad-border bg-cad-bg/50 text-[11px] font-mono text-cad-textMuted">
        <span>Selected Node: </span>
        <span className="text-violet-300 font-bold">{selectedNodeId || 'None'}</span>
      </div>

    </div>
  );
};
