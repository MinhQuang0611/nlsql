import { useEffect, useState } from 'react';
import { Checkbox, Input, Typography, Spin } from 'antd';
import styled from 'styled-components';

const { Text } = Typography;

const StyledLayout = styled.div`
  padding: 16px;
  display: flex;
  flex-direction: column;
  height: 100%;
`;

const StyledListWrapper = styled.div`
  flex: 1;
  overflow-y: auto;
  margin-top: 16px;

  .ant-list-item {
    padding: 8px;
    cursor: pointer;
    border-radius: 4px;
    transition: background 0.2s;

    &:hover {
      background-color: var(--gray-3);
    }
    
    &.selected {
      background-color: var(--blue-1);
      border: 1px solid var(--blue-5);
    }
  }
`;

interface Props {
  selectedTables: Set<string>;
  onToggleTable: (tableName: string) => void;
}

export default function TablesSidebar({ selectedTables, onToggleTable }: Props) {
  const [tables, setTables] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetch('/api/v1/tables')
      .then((res) => res.json())
      .then((data) => {
        setTables(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching tables:', err);
        setLoading(false);
      });
  }, []);

  const filteredTables = Object.keys(tables).filter(
    (name) =>
      name.toLowerCase().includes(search.toLowerCase()) ||
      tables[name]?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>Search Tables</div>
      <input
        placeholder="Type to filter tables..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="mb-4"
        style={{ padding: '4px', border: '1px solid #ccc', borderRadius: '4px' }}
      />
      
      <div style={{ fontWeight: 'bold', margin: '16px 0 8px 0' }}>Available Tables</div>
      {loading ? (
        <div className="d-flex justify-center py-10">
          Loading...
        </div>
      ) : (
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {filteredTables.length === 0 ? (
            <div style={{ padding: '16px', textAlign: 'center', color: '#888' }}>
              No tables found
            </div>
          ) : (
            filteredTables.map((name) => (
              <div
                key={name}
                className={`table-item ${selectedTables.has(name) ? 'selected' : ''}`}
                style={{ 
                  padding: '8px', 
                  cursor: 'pointer', 
                  display: 'flex', 
                  alignItems: 'center',
                  background: selectedTables.has(name) ? '#e6f7ff' : 'transparent',
                  border: selectedTables.has(name) ? '1px solid #91d5ff' : 'none',
                  borderRadius: '4px',
                  marginBottom: '4px'
                }}
                onClick={() => onToggleTable(name)}
              >
                <input type="checkbox" checked={selectedTables.has(name)} readOnly style={{ marginRight: '8px' }} />
                <div className="d-flex flex-column" style={{ overflow: 'hidden' }}>
                  <div style={{ fontWeight: 'bold', fontSize: '13px' }}>{name}</div>
                  <div style={{ fontSize: '11px', color: '#666', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {tables[name] || 'No description'}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
