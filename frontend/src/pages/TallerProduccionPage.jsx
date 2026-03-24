import React from 'react';
import DashboardLayout from '../components/DashboardLayout.jsx';
import TallerProduccion from '../components/TallerProduccion.jsx';

const TallerProduccionPage = () => {
  return (
    <DashboardLayout title="Taller y Producción">
      <div className="-m-4 md:-m-8">
        <TallerProduccion />
      </div>
    </DashboardLayout>
  );
};

export default TallerProduccionPage;
