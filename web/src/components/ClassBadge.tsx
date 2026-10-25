import React from 'react';
import { getClassColor } from '../constants';

interface ClassBadgeProps {
  name: string;
  count?: number;
}

export const ClassBadge: React.FC<ClassBadgeProps> = ({ name, count }) => {
  const color = getClassColor(name);
  return (
    <span className="badge">
      <span className="badge-dot" style={{ backgroundColor: color }} />
      <span>{name}</span>
      {count !== undefined && <span style={{ opacity: 0.65 }}>({count})</span>}
    </span>
  );
};
