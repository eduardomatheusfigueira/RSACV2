/// <reference types="vite/client" />
/// <reference types="react" />

import React from 'react'

declare global {
  namespace JSX {
    interface Element extends React.ReactElement<any, any> {}
  }
}
