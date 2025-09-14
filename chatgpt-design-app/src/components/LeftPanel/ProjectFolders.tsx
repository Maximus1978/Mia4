import React from 'react';

const ProjectFolders: React.FC = () => {
    const folders = [
        { id: 1, name: 'Project A' },
        { id: 2, name: 'Project B' },
        { id: 3, name: 'Project C' },
    ];

    return (
        <div className="project-folders">
            <h3>Project Folders</h3>
            <ul>
                {folders.map(folder => (
                    <li key={folder.id} className="folder-item">
                        {folder.name}
                    </li>
                ))}
            </ul>
        </div>
    );
};

export default ProjectFolders;