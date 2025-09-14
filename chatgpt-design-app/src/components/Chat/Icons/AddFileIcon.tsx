import React from 'react';

const AddFileIcon: React.FC = () => {
    return (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="add-file-icon"
        >
            <path d="M12 2v20M2 12h20" />
            <path d="M12 2l10 10H2z" />
        </svg>
    );
};

export default AddFileIcon;