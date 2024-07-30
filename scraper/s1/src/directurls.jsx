import React from 'react';

const FormComponent = ({ formData, handleUrlChange }) => {
    return (
        <div className="form-wrapper">
            <form className="form-container">
                <div className="form-group">
                    <label htmlFor="url1" className="form-label">Enter URL 1</label>
                    <input
                        type="url"
                        id="url1"
                        required
                        className="form-input"
                        name="url1"
                        value={formData.url1}
                        onChange={handleUrlChange}
                    />
                </div>

                <div className="form-group">
                    <label htmlFor="url2" className="form-label">Enter URL 2</label>
                    <input
                        type="url"
                        id="url2"
                        required
                        className="form-input"
                        name="url2"
                        value={formData.url2}
                        onChange={handleUrlChange}
                    />
                </div>

                <div className="form-group">
                    <label htmlFor="url3" className="form-label">Enter URL 3</label>
                    <input
                        type="url"
                        id="url3"
                        required
                        className="form-input"
                        name="url3"
                        value={formData.url3}
                        onChange={handleUrlChange}
                    />
                </div>
            </form>
        </div>
    );
};

export default FormComponent;
