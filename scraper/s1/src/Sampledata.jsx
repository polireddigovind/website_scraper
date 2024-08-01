import React from 'react';

const removeUrlPrefix = (url) => {
    return url.replace(/^https?:\/\/(www\.)?/, '');
};

const SampleTable = ({ data, openaimodel }) => {
    const isOpenAIModelPresent = openaimodel.length > 0;

    const midIndex = Math.ceil(data.length / 2);
    const firstTableData = isOpenAIModelPresent ? data.slice(0, midIndex) : data;
    const secondTableData = isOpenAIModelPresent ? data.slice(midIndex) : [];

    return (
        <div className='separate_tables'>
            <div className='sample_urls'>
                {firstTableData.length > 0 && (
                    <div className='table-container'>
                        <p>Results Displayed Using Groq API</p>
                        <table>
                            <thead>
                                <tr>
                                    <th>website</th>
                                    <th>Data</th>
                                </tr>
                            </thead>
                            <tbody>
                                {firstTableData.map((url, index) => (
                                    <tr key={index}>
                                        <td>{removeUrlPrefix(url.title)}</td>
                                        <td>{url.data}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
                {firstTableData.length === 0 && <p>No data available</p>}
            </div>
            <div className='sample_urls'>
                {secondTableData.length > 0 && (
                    <div className='table-container'>
                        <p>Results Displayed Using openai API</p>
                        <table>
                            <thead>
                                <tr>
                                    <th>website</th>
                                    <th>Data</th>
                                </tr>
                            </thead>
                            <tbody>
                                {secondTableData.map((url, index) => (
                                    <tr key={index}>
                                        <td>{removeUrlPrefix(url.title)}</td>
                                        <td>{url.data}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
                {secondTableData.length === 0 && <p>No data available</p>}
            </div>
        </div>
    );
};

export default SampleTable;
