/*
 * ATTENTION: An "eval-source-map" devtool has been used.
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file with attached SourceMaps in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
(() => {
var exports = {};
exports.id = "pages/_app";
exports.ids = ["pages/_app"];
exports.modules = {

/***/ "__barrel_optimize__?names=Spin!=!./src/import/antd.ts":
/*!*************************************************************!*\
  !*** __barrel_optimize__?names=Spin!=!./src/import/antd.ts ***!
  \*************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   Spin: () => (/* reexport safe */ antd_lib_spin__WEBPACK_IMPORTED_MODULE_0__[\"default\"])\n/* harmony export */ });\n/* harmony import */ var antd_lib_spin__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! antd/lib/spin */ \"./node_modules/antd/lib/spin/index.js\");\n\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiX19iYXJyZWxfb3B0aW1pemVfXz9uYW1lcz1TcGluIT0hLi9zcmMvaW1wb3J0L2FudGQudHMiLCJtYXBwaW5ncyI6Ijs7Ozs7QUFDK0MiLCJzb3VyY2VzIjpbIndlYnBhY2s6Ly93cmVuLXVpLy4vc3JjL2ltcG9ydC9hbnRkLnRzPzMwNzAiXSwic291cmNlc0NvbnRlbnQiOlsiXG5leHBvcnQgeyBkZWZhdWx0IGFzIFNwaW4gfSBmcm9tIFwiYW50ZC9saWIvc3BpblwiIl0sIm5hbWVzIjpbImRlZmF1bHQiLCJTcGluIl0sInNvdXJjZVJvb3QiOiIifQ==\n//# sourceURL=webpack-internal:///__barrel_optimize__?names=Spin!=!./src/import/antd.ts\n");

/***/ }),

/***/ "__barrel_optimize__?names=message!=!./src/import/antd.ts":
/*!****************************************************************!*\
  !*** __barrel_optimize__?names=message!=!./src/import/antd.ts ***!
  \****************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   message: () => (/* reexport safe */ antd_lib_message__WEBPACK_IMPORTED_MODULE_0__[\"default\"])\n/* harmony export */ });\n/* harmony import */ var antd_lib_message__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! antd/lib/message */ \"./node_modules/antd/lib/message/index.js\");\n\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiX19iYXJyZWxfb3B0aW1pemVfXz9uYW1lcz1tZXNzYWdlIT0hLi9zcmMvaW1wb3J0L2FudGQudHMiLCJtYXBwaW5ncyI6Ijs7Ozs7QUFDcUQiLCJzb3VyY2VzIjpbIndlYnBhY2s6Ly93cmVuLXVpLy4vc3JjL2ltcG9ydC9hbnRkLnRzPzMwNzAiXSwic291cmNlc0NvbnRlbnQiOlsiXG5leHBvcnQgeyBkZWZhdWx0IGFzIG1lc3NhZ2UgfSBmcm9tIFwiYW50ZC9saWIvbWVzc2FnZVwiIl0sIm5hbWVzIjpbImRlZmF1bHQiLCJtZXNzYWdlIl0sInNvdXJjZVJvb3QiOiIifQ==\n//# sourceURL=webpack-internal:///__barrel_optimize__?names=message!=!./src/import/antd.ts\n");

/***/ }),

/***/ "./src/apollo/client/index.ts":
/*!************************************!*\
  !*** ./src/apollo/client/index.ts ***!
  \************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"default\": () => (__WEBPACK_DEFAULT_EXPORT__)\n/* harmony export */ });\n/* harmony import */ var _apollo_client__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @apollo/client */ \"@apollo/client\");\n/* harmony import */ var _apollo_client__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_apollo_client__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var _apollo_client_link_error__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @apollo/client/link/error */ \"@apollo/client/link/error\");\n/* harmony import */ var _apollo_client_link_error__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_apollo_client_link_error__WEBPACK_IMPORTED_MODULE_1__);\n/* harmony import */ var _utils_errorHandler__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! @/utils/errorHandler */ \"./src/utils/errorHandler.tsx\");\n\n\n\nconst apolloErrorLink = (0,_apollo_client_link_error__WEBPACK_IMPORTED_MODULE_1__.onError)((error)=>(0,_utils_errorHandler__WEBPACK_IMPORTED_MODULE_2__[\"default\"])(error));\nconst httpLink = new _apollo_client__WEBPACK_IMPORTED_MODULE_0__.HttpLink({\n    uri: \"/api/graphql\"\n});\nconst client = new _apollo_client__WEBPACK_IMPORTED_MODULE_0__.ApolloClient({\n    link: (0,_apollo_client__WEBPACK_IMPORTED_MODULE_0__.from)([\n        apolloErrorLink,\n        httpLink\n    ]),\n    cache: new _apollo_client__WEBPACK_IMPORTED_MODULE_0__.InMemoryCache()\n});\n/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (client);\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiLi9zcmMvYXBvbGxvL2NsaWVudC9pbmRleC50cyIsIm1hcHBpbmdzIjoiOzs7Ozs7Ozs7QUFBNkU7QUFDekI7QUFDSjtBQUVoRCxNQUFNTSxrQkFBa0JGLGtFQUFPQSxDQUFDLENBQUNHLFFBQVVGLCtEQUFZQSxDQUFDRTtBQUV4RCxNQUFNQyxXQUFXLElBQUlQLG9EQUFRQSxDQUFDO0lBQzVCUSxLQUFLO0FBQ1A7QUFFQSxNQUFNQyxTQUFTLElBQUlWLHdEQUFZQSxDQUFDO0lBQzlCVyxNQUFNUixvREFBSUEsQ0FBQztRQUFDRztRQUFpQkU7S0FBUztJQUN0Q0ksT0FBTyxJQUFJVix5REFBYUE7QUFDMUI7QUFFQSxpRUFBZVEsTUFBTUEsRUFBQyIsInNvdXJjZXMiOlsid2VicGFjazovL3dyZW4tdWkvLi9zcmMvYXBvbGxvL2NsaWVudC9pbmRleC50cz9kMTYyIl0sInNvdXJjZXNDb250ZW50IjpbImltcG9ydCB7IEFwb2xsb0NsaWVudCwgSHR0cExpbmssIEluTWVtb3J5Q2FjaGUsIGZyb20gfSBmcm9tICdAYXBvbGxvL2NsaWVudCc7XG5pbXBvcnQgeyBvbkVycm9yIH0gZnJvbSAnQGFwb2xsby9jbGllbnQvbGluay9lcnJvcic7XG5pbXBvcnQgZXJyb3JIYW5kbGVyIGZyb20gJ0AvdXRpbHMvZXJyb3JIYW5kbGVyJztcblxuY29uc3QgYXBvbGxvRXJyb3JMaW5rID0gb25FcnJvcigoZXJyb3IpID0+IGVycm9ySGFuZGxlcihlcnJvcikpO1xuXG5jb25zdCBodHRwTGluayA9IG5ldyBIdHRwTGluayh7XG4gIHVyaTogJy9hcGkvZ3JhcGhxbCcsXG59KTtcblxuY29uc3QgY2xpZW50ID0gbmV3IEFwb2xsb0NsaWVudCh7XG4gIGxpbms6IGZyb20oW2Fwb2xsb0Vycm9yTGluaywgaHR0cExpbmtdKSxcbiAgY2FjaGU6IG5ldyBJbk1lbW9yeUNhY2hlKCksXG59KTtcblxuZXhwb3J0IGRlZmF1bHQgY2xpZW50O1xuIl0sIm5hbWVzIjpbIkFwb2xsb0NsaWVudCIsIkh0dHBMaW5rIiwiSW5NZW1vcnlDYWNoZSIsImZyb20iLCJvbkVycm9yIiwiZXJyb3JIYW5kbGVyIiwiYXBvbGxvRXJyb3JMaW5rIiwiZXJyb3IiLCJodHRwTGluayIsInVyaSIsImNsaWVudCIsImxpbmsiLCJjYWNoZSJdLCJzb3VyY2VSb290IjoiIn0=\n//# sourceURL=webpack-internal:///./src/apollo/client/index.ts\n");

/***/ }),

/***/ "./src/components/PageLoading.tsx":
/*!****************************************!*\
  !*** ./src/components/PageLoading.tsx ***!
  \****************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   FlexLoading: () => (/* binding */ FlexLoading),\n/* harmony export */   Loading: () => (/* binding */ Loading),\n/* harmony export */   LoadingWrapper: () => (/* binding */ LoadingWrapper),\n/* harmony export */   Spinner: () => (/* binding */ Spinner),\n/* harmony export */   \"default\": () => (/* binding */ PageLoading),\n/* harmony export */   defaultIndicator: () => (/* binding */ defaultIndicator)\n/* harmony export */ });\n/* harmony import */ var react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react/jsx-dev-runtime */ \"react/jsx-dev-runtime\");\n/* harmony import */ var react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var _barrel_optimize_names_Spin_antd__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! __barrel_optimize__?names=Spin!=!antd */ \"__barrel_optimize__?names=Spin!=!./src/import/antd.ts\");\n/* harmony import */ var styled_components__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! styled-components */ \"styled-components\");\n/* harmony import */ var styled_components__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(styled_components__WEBPACK_IMPORTED_MODULE_2__);\n/* harmony import */ var _ant_design_icons_LoadingOutlined__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! @ant-design/icons/LoadingOutlined */ \"./node_modules/@ant-design/icons/LoadingOutlined.js\");\n/* harmony import */ var _ant_design_icons_LoadingOutlined__WEBPACK_IMPORTED_MODULE_3___default = /*#__PURE__*/__webpack_require__.n(_ant_design_icons_LoadingOutlined__WEBPACK_IMPORTED_MODULE_3__);\n\n\n\n\nconst Wrapper = styled_components__WEBPACK_IMPORTED_MODULE_2___default().div.withConfig({\n    displayName: \"PageLoading__Wrapper\",\n    componentId: \"sc-673bb2dd-0\"\n})([\n    \"--color-primary:#bc2626;position:absolute;top:48px;left:0;right:0;bottom:0;z-index:9999;background-color:white;display:none;&.isShow{display:flex;}.circle-loader{width:50px;aspect-ratio:1;--c:no-repeat radial-gradient(farthest-side,var(--color-primary) 92%,#0000);background:var(--c) 50% 0,var(--c) 50% 100%,var(--c) 100% 50%,var(--c) 0 50%;background-size:10px 10px;animation:l18 1s infinite;position:relative;}.circle-loader::before{content:'';position:absolute;inset:0;margin:3px;background:repeating-conic-gradient( #0000 0 35deg,var(--color-primary) 0 90deg );-webkit-mask:radial-gradient(farthest-side,#0000 calc(100% - 3px),#000 0);border-radius:50%;}@keyframes l18{100%{transform:rotate(0.5turn);}}\"\n]);\nconst defaultIndicator = /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)((_ant_design_icons_LoadingOutlined__WEBPACK_IMPORTED_MODULE_3___default()), {\n    style: {\n        fontSize: 36\n    },\n    spin: true\n}, void 0, false, {\n    fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/components/PageLoading.tsx\",\n    lineNumber: 70,\n    columnNumber: 3\n}, undefined);\nconst Spinner = ({ className = \"\", size = 36 })=>/*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)((_ant_design_icons_LoadingOutlined__WEBPACK_IMPORTED_MODULE_3___default()), {\n        className: className,\n        style: {\n            fontSize: size\n        },\n        spin: true\n    }, void 0, false, {\n        fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/components/PageLoading.tsx\",\n        lineNumber: 74,\n        columnNumber: 3\n    }, undefined);\nfunction PageLoading(props) {\n    const { visible } = props;\n    return /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(Wrapper, {\n        className: `align-center justify-center${visible ? \" isShow\" : \"\"}`,\n        children: /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"div\", {\n            className: \"text-center\",\n            children: [\n                /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"div\", {\n                    className: \"circle-loader\"\n                }, void 0, false, {\n                    fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/components/PageLoading.tsx\",\n                    lineNumber: 84,\n                    columnNumber: 9\n                }, this),\n                /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"div\", {\n                    className: \"mt-2 geekblue-6\",\n                    children: \"Loading...\"\n                }, void 0, false, {\n                    fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/components/PageLoading.tsx\",\n                    lineNumber: 85,\n                    columnNumber: 9\n                }, this)\n            ]\n        }, void 0, true, {\n            fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/components/PageLoading.tsx\",\n            lineNumber: 83,\n            columnNumber: 7\n        }, this)\n    }, void 0, false, {\n        fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/components/PageLoading.tsx\",\n        lineNumber: 80,\n        columnNumber: 5\n    }, this);\n}\nconst FlexLoading = (props)=>{\n    const { height, tip } = props;\n    return /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"div\", {\n        className: \"d-flex align-center justify-center flex-column geekblue-6\",\n        style: {\n            height: height || \"100%\"\n        },\n        children: [\n            defaultIndicator,\n            tip && /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"span\", {\n                className: \"mt-2\",\n                children: tip\n            }, void 0, false, {\n                fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/components/PageLoading.tsx\",\n                lineNumber: 99,\n                columnNumber: 15\n            }, undefined)\n        ]\n    }, void 0, true, {\n        fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/components/PageLoading.tsx\",\n        lineNumber: 94,\n        columnNumber: 5\n    }, undefined);\n};\nconst Loading = ({ children = null, spinning = false, loading = false, tip })=>/*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(_barrel_optimize_names_Spin_antd__WEBPACK_IMPORTED_MODULE_1__.Spin, {\n        indicator: defaultIndicator,\n        spinning: spinning || loading,\n        tip: tip,\n        children: children\n    }, void 0, false, {\n        fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/components/PageLoading.tsx\",\n        lineNumber: 110,\n        columnNumber: 3\n    }, undefined);\nconst LoadingWrapper = (props)=>{\n    const { loading, tip, children } = props;\n    if (loading) return /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(FlexLoading, {\n        tip: tip\n    }, void 0, false, {\n        fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/components/PageLoading.tsx\",\n        lineNumber: 123,\n        columnNumber: 23\n    }, undefined);\n    return children;\n};\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiLi9zcmMvY29tcG9uZW50cy9QYWdlTG9hZGluZy50c3giLCJtYXBwaW5ncyI6Ijs7Ozs7Ozs7Ozs7Ozs7Ozs7QUFBNEI7QUFDVztBQUN5QjtBQUVoRSxNQUFNRyxVQUFVRiw0REFBVTs7Ozs7O0FBZ0VuQixNQUFNSSxpQ0FDWCw4REFBQ0gsMEVBQWVBO0lBQUNJLE9BQU87UUFBRUMsVUFBVTtJQUFHO0lBQUdDLElBQUk7Ozs7O2NBQzlDO0FBRUssTUFBTUMsVUFBVSxDQUFDLEVBQUVDLFlBQVksRUFBRSxFQUFFQyxPQUFPLEVBQUUsRUFBRSxpQkFDbkQsOERBQUNULDBFQUFlQTtRQUFDUSxXQUFXQTtRQUFXSixPQUFPO1lBQUVDLFVBQVVJO1FBQUs7UUFBR0gsSUFBSTs7Ozs7a0JBQ3RFO0FBRWEsU0FBU0ksWUFBWUMsS0FBWTtJQUM5QyxNQUFNLEVBQUVDLE9BQU8sRUFBRSxHQUFHRDtJQUNwQixxQkFDRSw4REFBQ1Y7UUFDQ08sV0FBVyxDQUFDLDJCQUEyQixFQUFFSSxVQUFVLFlBQVksR0FBRyxDQUFDO2tCQUVuRSw0RUFBQ1Y7WUFBSU0sV0FBVTs7OEJBQ2IsOERBQUNOO29CQUFJTSxXQUFVOzs7Ozs7OEJBQ2YsOERBQUNOO29CQUFJTSxXQUFVOzhCQUFrQjs7Ozs7Ozs7Ozs7Ozs7Ozs7QUFJekM7QUFFTyxNQUFNSyxjQUFjLENBQUNGO0lBQzFCLE1BQU0sRUFBRUcsTUFBTSxFQUFFQyxHQUFHLEVBQUUsR0FBR0o7SUFDeEIscUJBQ0UsOERBQUNUO1FBQ0NNLFdBQVU7UUFDVkosT0FBTztZQUFFVSxRQUFRQSxVQUFVO1FBQU87O1lBRWpDWDtZQUNBWSxxQkFBTyw4REFBQ0M7Z0JBQUtSLFdBQVU7MEJBQVFPOzs7Ozs7Ozs7Ozs7QUFHdEMsRUFBRTtBQUVLLE1BQU1FLFVBQVUsQ0FBQyxFQUN0QkMsV0FBVyxJQUFJLEVBQ2ZDLFdBQVcsS0FBSyxFQUNoQkMsVUFBVSxLQUFLLEVBQ2ZMLEdBQUcsRUFDVSxpQkFDYiw4REFBQ2pCLGtFQUFJQTtRQUFDdUIsV0FBV2xCO1FBQWtCZ0IsVUFBVUEsWUFBWUM7UUFBU0wsS0FBS0E7a0JBQ3BFRzs7Ozs7a0JBRUg7QUFRSyxNQUFNSSxpQkFBaUIsQ0FBQ1g7SUFDN0IsTUFBTSxFQUFFUyxPQUFPLEVBQUVMLEdBQUcsRUFBRUcsUUFBUSxFQUFFLEdBQUdQO0lBQ25DLElBQUlTLFNBQVMscUJBQU8sOERBQUNQO1FBQVlFLEtBQUtBOzs7Ozs7SUFDdEMsT0FBT0c7QUFDVCxFQUFFIiwic291cmNlcyI6WyJ3ZWJwYWNrOi8vd3Jlbi11aS8uL3NyYy9jb21wb25lbnRzL1BhZ2VMb2FkaW5nLnRzeD9kZjc0Il0sInNvdXJjZXNDb250ZW50IjpbImltcG9ydCB7IFNwaW4gfSBmcm9tICdhbnRkJztcbmltcG9ydCBzdHlsZWQgZnJvbSAnc3R5bGVkLWNvbXBvbmVudHMnO1xuaW1wb3J0IExvYWRpbmdPdXRsaW5lZCBmcm9tICdAYW50LWRlc2lnbi9pY29ucy9Mb2FkaW5nT3V0bGluZWQnO1xuXG5jb25zdCBXcmFwcGVyID0gc3R5bGVkLmRpdmBcbiAgLS1jb2xvci1wcmltYXJ5OiAjYmMyNjI2O1xuICBwb3NpdGlvbjogYWJzb2x1dGU7XG4gIHRvcDogNDhweDtcbiAgbGVmdDogMDtcbiAgcmlnaHQ6IDA7XG4gIGJvdHRvbTogMDtcbiAgei1pbmRleDogOTk5OTtcbiAgYmFja2dyb3VuZC1jb2xvcjogd2hpdGU7XG4gIGRpc3BsYXk6IG5vbmU7XG5cbiAgJi5pc1Nob3cge1xuICAgIGRpc3BsYXk6IGZsZXg7XG4gIH1cblxuICAuY2lyY2xlLWxvYWRlciB7XG4gICAgd2lkdGg6IDUwcHg7XG4gICAgYXNwZWN0LXJhdGlvOiAxO1xuICAgIC0tYzogbm8tcmVwZWF0IHJhZGlhbC1ncmFkaWVudChmYXJ0aGVzdC1zaWRlLCB2YXIoLS1jb2xvci1wcmltYXJ5KSA5MiUsICMwMDAwKTtcbiAgICBiYWNrZ3JvdW5kOlxuICAgICAgdmFyKC0tYykgNTAlIDAsXG4gICAgICB2YXIoLS1jKSA1MCUgMTAwJSxcbiAgICAgIHZhcigtLWMpIDEwMCUgNTAlLFxuICAgICAgdmFyKC0tYykgMCA1MCU7XG4gICAgYmFja2dyb3VuZC1zaXplOiAxMHB4IDEwcHg7XG4gICAgYW5pbWF0aW9uOiBsMTggMXMgaW5maW5pdGU7XG4gICAgcG9zaXRpb246IHJlbGF0aXZlO1xuICB9XG5cbiAgLmNpcmNsZS1sb2FkZXI6OmJlZm9yZSB7XG4gICAgY29udGVudDogJyc7XG4gICAgcG9zaXRpb246IGFic29sdXRlO1xuICAgIGluc2V0OiAwO1xuICAgIG1hcmdpbjogM3B4O1xuICAgIGJhY2tncm91bmQ6IHJlcGVhdGluZy1jb25pYy1ncmFkaWVudChcbiAgICAgICMwMDAwIDAgMzVkZWcsXG4gICAgICB2YXIoLS1jb2xvci1wcmltYXJ5KSAwIDkwZGVnXG4gICAgKTtcbiAgICAtd2Via2l0LW1hc2s6IHJhZGlhbC1ncmFkaWVudChmYXJ0aGVzdC1zaWRlLCAjMDAwMCBjYWxjKDEwMCUgLSAzcHgpLCAjMDAwIDApO1xuICAgIGJvcmRlci1yYWRpdXM6IDUwJTtcbiAgfVxuXG4gIEBrZXlmcmFtZXMgbDE4IHtcbiAgICAxMDAlIHtcbiAgICAgIHRyYW5zZm9ybTogcm90YXRlKDAuNXR1cm4pO1xuICAgIH1cbiAgfVxuYDtcblxuaW50ZXJmYWNlIFByb3BzIHtcbiAgdmlzaWJsZT86IGJvb2xlYW47XG59XG5cbmludGVyZmFjZSBMb2FkaW5nUHJvcHMge1xuICBjaGlsZHJlbj86IFJlYWN0LlJlYWN0Tm9kZSB8IG51bGw7XG4gIHNwaW5uaW5nPzogYm9vbGVhbjtcbiAgbG9hZGluZz86IGJvb2xlYW47XG4gIHRpcD86IHN0cmluZztcbiAgc2l6ZT86IG51bWJlcjtcbiAgd2lkdGg/OiBudW1iZXI7XG4gIGhlaWdodD86IG51bWJlcjtcbiAgY2xhc3NOYW1lPzogc3RyaW5nO1xufVxuXG5leHBvcnQgY29uc3QgZGVmYXVsdEluZGljYXRvciA9IChcbiAgPExvYWRpbmdPdXRsaW5lZCBzdHlsZT17eyBmb250U2l6ZTogMzYgfX0gc3BpbiAvPlxuKTtcblxuZXhwb3J0IGNvbnN0IFNwaW5uZXIgPSAoeyBjbGFzc05hbWUgPSAnJywgc2l6ZSA9IDM2IH0pID0+IChcbiAgPExvYWRpbmdPdXRsaW5lZCBjbGFzc05hbWU9e2NsYXNzTmFtZX0gc3R5bGU9e3sgZm9udFNpemU6IHNpemUgfX0gc3BpbiAvPlxuKTtcblxuZXhwb3J0IGRlZmF1bHQgZnVuY3Rpb24gUGFnZUxvYWRpbmcocHJvcHM6IFByb3BzKSB7XG4gIGNvbnN0IHsgdmlzaWJsZSB9ID0gcHJvcHM7XG4gIHJldHVybiAoXG4gICAgPFdyYXBwZXJcbiAgICAgIGNsYXNzTmFtZT17YGFsaWduLWNlbnRlciBqdXN0aWZ5LWNlbnRlciR7dmlzaWJsZSA/ICcgaXNTaG93JyA6ICcnfWB9XG4gICAgPlxuICAgICAgPGRpdiBjbGFzc05hbWU9XCJ0ZXh0LWNlbnRlclwiPlxuICAgICAgICA8ZGl2IGNsYXNzTmFtZT1cImNpcmNsZS1sb2FkZXJcIiAvPlxuICAgICAgICA8ZGl2IGNsYXNzTmFtZT1cIm10LTIgZ2Vla2JsdWUtNlwiPkxvYWRpbmcuLi48L2Rpdj5cbiAgICAgIDwvZGl2PlxuICAgIDwvV3JhcHBlcj5cbiAgKTtcbn1cblxuZXhwb3J0IGNvbnN0IEZsZXhMb2FkaW5nID0gKHByb3BzKSA9PiB7XG4gIGNvbnN0IHsgaGVpZ2h0LCB0aXAgfSA9IHByb3BzO1xuICByZXR1cm4gKFxuICAgIDxkaXZcbiAgICAgIGNsYXNzTmFtZT1cImQtZmxleCBhbGlnbi1jZW50ZXIganVzdGlmeS1jZW50ZXIgZmxleC1jb2x1bW4gZ2Vla2JsdWUtNlwiXG4gICAgICBzdHlsZT17eyBoZWlnaHQ6IGhlaWdodCB8fCAnMTAwJScgfX1cbiAgICA+XG4gICAgICB7ZGVmYXVsdEluZGljYXRvcn1cbiAgICAgIHt0aXAgJiYgPHNwYW4gY2xhc3NOYW1lPVwibXQtMlwiPnt0aXB9PC9zcGFuPn1cbiAgICA8L2Rpdj5cbiAgKTtcbn07XG5cbmV4cG9ydCBjb25zdCBMb2FkaW5nID0gKHtcbiAgY2hpbGRyZW4gPSBudWxsLFxuICBzcGlubmluZyA9IGZhbHNlLFxuICBsb2FkaW5nID0gZmFsc2UsXG4gIHRpcCxcbn06IExvYWRpbmdQcm9wcykgPT4gKFxuICA8U3BpbiBpbmRpY2F0b3I9e2RlZmF1bHRJbmRpY2F0b3J9IHNwaW5uaW5nPXtzcGlubmluZyB8fCBsb2FkaW5nfSB0aXA9e3RpcH0+XG4gICAge2NoaWxkcmVufVxuICA8L1NwaW4+XG4pO1xuXG5pbnRlcmZhY2UgTG9hZGluZ1dyYXBwZXJQcm9wcyB7XG4gIGxvYWRpbmc6IGJvb2xlYW47XG4gIHRpcD86IHN0cmluZztcbiAgY2hpbGRyZW46IFJlYWN0LlJlYWN0RWxlbWVudDtcbn1cblxuZXhwb3J0IGNvbnN0IExvYWRpbmdXcmFwcGVyID0gKHByb3BzOiBMb2FkaW5nV3JhcHBlclByb3BzKSA9PiB7XG4gIGNvbnN0IHsgbG9hZGluZywgdGlwLCBjaGlsZHJlbiB9ID0gcHJvcHM7XG4gIGlmIChsb2FkaW5nKSByZXR1cm4gPEZsZXhMb2FkaW5nIHRpcD17dGlwfSAvPjtcbiAgcmV0dXJuIGNoaWxkcmVuO1xufTtcbiJdLCJuYW1lcyI6WyJTcGluIiwic3R5bGVkIiwiTG9hZGluZ091dGxpbmVkIiwiV3JhcHBlciIsImRpdiIsImRlZmF1bHRJbmRpY2F0b3IiLCJzdHlsZSIsImZvbnRTaXplIiwic3BpbiIsIlNwaW5uZXIiLCJjbGFzc05hbWUiLCJzaXplIiwiUGFnZUxvYWRpbmciLCJwcm9wcyIsInZpc2libGUiLCJGbGV4TG9hZGluZyIsImhlaWdodCIsInRpcCIsInNwYW4iLCJMb2FkaW5nIiwiY2hpbGRyZW4iLCJzcGlubmluZyIsImxvYWRpbmciLCJpbmRpY2F0b3IiLCJMb2FkaW5nV3JhcHBlciJdLCJzb3VyY2VSb290IjoiIn0=\n//# sourceURL=webpack-internal:///./src/components/PageLoading.tsx\n");

/***/ }),

/***/ "./src/hooks/useGlobalConfig.tsx":
/*!***************************************!*\
  !*** ./src/hooks/useGlobalConfig.tsx ***!
  \***************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   GlobalConfigProvider: () => (/* binding */ GlobalConfigProvider),\n/* harmony export */   \"default\": () => (/* binding */ useGlobalConfig)\n/* harmony export */ });\n/* harmony import */ var react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react/jsx-dev-runtime */ \"react/jsx-dev-runtime\");\n/* harmony import */ var react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var next_router__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! next/router */ \"./node_modules/next/router.js\");\n/* harmony import */ var next_router__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(next_router__WEBPACK_IMPORTED_MODULE_1__);\n/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! react */ \"react\");\n/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(react__WEBPACK_IMPORTED_MODULE_2__);\n/* harmony import */ var _utils_env__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! @/utils/env */ \"./src/utils/env.ts\");\n/* harmony import */ var _utils_telemetry__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! @/utils/telemetry */ \"./src/utils/telemetry.ts\");\n\n\n\n\n\nconst GlobalConfigContext = /*#__PURE__*/ (0,react__WEBPACK_IMPORTED_MODULE_2__.createContext)({});\nconst GlobalConfigProvider = ({ children })=>{\n    const router = (0,next_router__WEBPACK_IMPORTED_MODULE_1__.useRouter)();\n    const [config, setConfig] = (0,react__WEBPACK_IMPORTED_MODULE_2__.useState)(null);\n    (0,react__WEBPACK_IMPORTED_MODULE_2__.useEffect)(()=>{\n        (0,_utils_env__WEBPACK_IMPORTED_MODULE_3__.getUserConfig)().then((config)=>{\n            setConfig(config);\n            // telemetry setup\n            const cleanup = (0,_utils_telemetry__WEBPACK_IMPORTED_MODULE_4__.trackUserTelemetry)(router, config);\n            return cleanup;\n        }).catch((error)=>{\n            console.error(\"Failed to get user config\", error);\n        });\n    }, [\n        router\n    ]);\n    const value = {\n        config\n    };\n    return /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(GlobalConfigContext.Provider, {\n        value: value,\n        children: children\n    }, void 0, false, {\n        fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/hooks/useGlobalConfig.tsx\",\n        lineNumber: 34,\n        columnNumber: 5\n    }, undefined);\n};\nfunction useGlobalConfig() {\n    return (0,react__WEBPACK_IMPORTED_MODULE_2__.useContext)(GlobalConfigContext);\n}\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiLi9zcmMvaG9va3MvdXNlR2xvYmFsQ29uZmlnLnRzeCIsIm1hcHBpbmdzIjoiOzs7Ozs7Ozs7Ozs7OztBQUF3QztBQUMrQjtBQUNmO0FBQ0Q7QUFNdkQsTUFBTU8sb0NBQXNCTixvREFBYUEsQ0FBZSxDQUFDO0FBRWxELE1BQU1PLHVCQUF1QixDQUFDLEVBQUVDLFFBQVEsRUFBRTtJQUMvQyxNQUFNQyxTQUFTVixzREFBU0E7SUFDeEIsTUFBTSxDQUFDVyxRQUFRQyxVQUFVLEdBQUdSLCtDQUFRQSxDQUFvQjtJQUV4REQsZ0RBQVNBLENBQUM7UUFDUkUseURBQWFBLEdBQ1ZRLElBQUksQ0FBQyxDQUFDRjtZQUNMQyxVQUFVRDtZQUNWLGtCQUFrQjtZQUNsQixNQUFNRyxVQUFVUixvRUFBa0JBLENBQUNJLFFBQVFDO1lBQzNDLE9BQU9HO1FBQ1QsR0FDQ0MsS0FBSyxDQUFDLENBQUNDO1lBQ05DLFFBQVFELEtBQUssQ0FBQyw2QkFBNkJBO1FBQzdDO0lBQ0osR0FBRztRQUFDTjtLQUFPO0lBRVgsTUFBTVEsUUFBUTtRQUNaUDtJQUNGO0lBRUEscUJBQ0UsOERBQUNKLG9CQUFvQlksUUFBUTtRQUFDRCxPQUFPQTtrQkFDbENUOzs7Ozs7QUFHUCxFQUFFO0FBRWEsU0FBU1c7SUFDdEIsT0FBT2xCLGlEQUFVQSxDQUFDSztBQUNwQiIsInNvdXJjZXMiOlsid2VicGFjazovL3dyZW4tdWkvLi9zcmMvaG9va3MvdXNlR2xvYmFsQ29uZmlnLnRzeD9hMjUyIl0sInNvdXJjZXNDb250ZW50IjpbImltcG9ydCB7IHVzZVJvdXRlciB9IGZyb20gJ25leHQvcm91dGVyJztcbmltcG9ydCB7IGNyZWF0ZUNvbnRleHQsIHVzZUNvbnRleHQsIHVzZUVmZmVjdCwgdXNlU3RhdGUgfSBmcm9tICdyZWFjdCc7XG5pbXBvcnQgeyBnZXRVc2VyQ29uZmlnLCBVc2VyQ29uZmlnIH0gZnJvbSAnQC91dGlscy9lbnYnO1xuaW1wb3J0IHsgdHJhY2tVc2VyVGVsZW1ldHJ5IH0gZnJvbSAnQC91dGlscy90ZWxlbWV0cnknO1xuXG50eXBlIENvbnRleHRQcm9wcyA9IHtcbiAgY29uZmlnPzogVXNlckNvbmZpZyB8IG51bGw7XG59O1xuXG5jb25zdCBHbG9iYWxDb25maWdDb250ZXh0ID0gY3JlYXRlQ29udGV4dDxDb250ZXh0UHJvcHM+KHt9KTtcblxuZXhwb3J0IGNvbnN0IEdsb2JhbENvbmZpZ1Byb3ZpZGVyID0gKHsgY2hpbGRyZW4gfSkgPT4ge1xuICBjb25zdCByb3V0ZXIgPSB1c2VSb3V0ZXIoKTtcbiAgY29uc3QgW2NvbmZpZywgc2V0Q29uZmlnXSA9IHVzZVN0YXRlPFVzZXJDb25maWcgfCBudWxsPihudWxsKTtcblxuICB1c2VFZmZlY3QoKCkgPT4ge1xuICAgIGdldFVzZXJDb25maWcoKVxuICAgICAgLnRoZW4oKGNvbmZpZykgPT4ge1xuICAgICAgICBzZXRDb25maWcoY29uZmlnKTtcbiAgICAgICAgLy8gdGVsZW1ldHJ5IHNldHVwXG4gICAgICAgIGNvbnN0IGNsZWFudXAgPSB0cmFja1VzZXJUZWxlbWV0cnkocm91dGVyLCBjb25maWcpO1xuICAgICAgICByZXR1cm4gY2xlYW51cDtcbiAgICAgIH0pXG4gICAgICAuY2F0Y2goKGVycm9yKSA9PiB7XG4gICAgICAgIGNvbnNvbGUuZXJyb3IoJ0ZhaWxlZCB0byBnZXQgdXNlciBjb25maWcnLCBlcnJvcik7XG4gICAgICB9KTtcbiAgfSwgW3JvdXRlcl0pO1xuXG4gIGNvbnN0IHZhbHVlID0ge1xuICAgIGNvbmZpZyxcbiAgfTtcblxuICByZXR1cm4gKFxuICAgIDxHbG9iYWxDb25maWdDb250ZXh0LlByb3ZpZGVyIHZhbHVlPXt2YWx1ZX0+XG4gICAgICB7Y2hpbGRyZW59XG4gICAgPC9HbG9iYWxDb25maWdDb250ZXh0LlByb3ZpZGVyPlxuICApO1xufTtcblxuZXhwb3J0IGRlZmF1bHQgZnVuY3Rpb24gdXNlR2xvYmFsQ29uZmlnKCkge1xuICByZXR1cm4gdXNlQ29udGV4dChHbG9iYWxDb25maWdDb250ZXh0KTtcbn1cbiJdLCJuYW1lcyI6WyJ1c2VSb3V0ZXIiLCJjcmVhdGVDb250ZXh0IiwidXNlQ29udGV4dCIsInVzZUVmZmVjdCIsInVzZVN0YXRlIiwiZ2V0VXNlckNvbmZpZyIsInRyYWNrVXNlclRlbGVtZXRyeSIsIkdsb2JhbENvbmZpZ0NvbnRleHQiLCJHbG9iYWxDb25maWdQcm92aWRlciIsImNoaWxkcmVuIiwicm91dGVyIiwiY29uZmlnIiwic2V0Q29uZmlnIiwidGhlbiIsImNsZWFudXAiLCJjYXRjaCIsImVycm9yIiwiY29uc29sZSIsInZhbHVlIiwiUHJvdmlkZXIiLCJ1c2VHbG9iYWxDb25maWciXSwic291cmNlUm9vdCI6IiJ9\n//# sourceURL=webpack-internal:///./src/hooks/useGlobalConfig.tsx\n");

/***/ }),

/***/ "./src/pages/_app.tsx":
/*!****************************!*\
  !*** ./src/pages/_app.tsx ***!
  \****************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"default\": () => (__WEBPACK_DEFAULT_EXPORT__)\n/* harmony export */ });\n/* harmony import */ var react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react/jsx-dev-runtime */ \"react/jsx-dev-runtime\");\n/* harmony import */ var react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var next_head__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! next/head */ \"next/head\");\n/* harmony import */ var next_head__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(next_head__WEBPACK_IMPORTED_MODULE_1__);\n/* harmony import */ var _barrel_optimize_names_Spin_antd__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! __barrel_optimize__?names=Spin!=!antd */ \"__barrel_optimize__?names=Spin!=!./src/import/antd.ts\");\n/* harmony import */ var posthog_js__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! posthog-js */ \"posthog-js\");\n/* harmony import */ var posthog_js__WEBPACK_IMPORTED_MODULE_3___default = /*#__PURE__*/__webpack_require__.n(posthog_js__WEBPACK_IMPORTED_MODULE_3__);\n/* harmony import */ var _apollo_client__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! @/apollo/client */ \"./src/apollo/client/index.ts\");\n/* harmony import */ var _hooks_useGlobalConfig__WEBPACK_IMPORTED_MODULE_5__ = __webpack_require__(/*! @/hooks/useGlobalConfig */ \"./src/hooks/useGlobalConfig.tsx\");\n/* harmony import */ var posthog_js_react__WEBPACK_IMPORTED_MODULE_6__ = __webpack_require__(/*! posthog-js/react */ \"posthog-js/react\");\n/* harmony import */ var posthog_js_react__WEBPACK_IMPORTED_MODULE_6___default = /*#__PURE__*/__webpack_require__.n(posthog_js_react__WEBPACK_IMPORTED_MODULE_6__);\n/* harmony import */ var _apollo_client__WEBPACK_IMPORTED_MODULE_7__ = __webpack_require__(/*! @apollo/client */ \"@apollo/client\");\n/* harmony import */ var _apollo_client__WEBPACK_IMPORTED_MODULE_7___default = /*#__PURE__*/__webpack_require__.n(_apollo_client__WEBPACK_IMPORTED_MODULE_7__);\n/* harmony import */ var _components_PageLoading__WEBPACK_IMPORTED_MODULE_8__ = __webpack_require__(/*! @/components/PageLoading */ \"./src/components/PageLoading.tsx\");\n\n\n\n\n\n\n\n\n\n__webpack_require__(/*! ../styles/index.less */ \"./src/styles/index.less\");\n_barrel_optimize_names_Spin_antd__WEBPACK_IMPORTED_MODULE_2__.Spin.setDefaultIndicator(_components_PageLoading__WEBPACK_IMPORTED_MODULE_8__.defaultIndicator);\nfunction App({ Component, pageProps }) {\n    return /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.Fragment, {\n        children: [\n            /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)((next_head__WEBPACK_IMPORTED_MODULE_1___default()), {\n                children: [\n                    /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"title\", {\n                        children: \"PTIT AI\"\n                    }, void 0, false, {\n                        fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/pages/_app.tsx\",\n                        lineNumber: 19,\n                        columnNumber: 9\n                    }, this),\n                    /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"link\", {\n                        rel: \"icon\",\n                        href: \"/favicon.ico\"\n                    }, void 0, false, {\n                        fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/pages/_app.tsx\",\n                        lineNumber: 20,\n                        columnNumber: 9\n                    }, this)\n                ]\n            }, void 0, true, {\n                fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/pages/_app.tsx\",\n                lineNumber: 18,\n                columnNumber: 7\n            }, this),\n            /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(_hooks_useGlobalConfig__WEBPACK_IMPORTED_MODULE_5__.GlobalConfigProvider, {\n                children: /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(_apollo_client__WEBPACK_IMPORTED_MODULE_7__.ApolloProvider, {\n                    client: _apollo_client__WEBPACK_IMPORTED_MODULE_4__[\"default\"],\n                    children: /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(posthog_js_react__WEBPACK_IMPORTED_MODULE_6__.PostHogProvider, {\n                        client: (posthog_js__WEBPACK_IMPORTED_MODULE_3___default()),\n                        children: /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"main\", {\n                            className: \"app\",\n                            children: /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(Component, {\n                                ...pageProps\n                            }, void 0, false, {\n                                fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/pages/_app.tsx\",\n                                lineNumber: 26,\n                                columnNumber: 15\n                            }, this)\n                        }, void 0, false, {\n                            fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/pages/_app.tsx\",\n                            lineNumber: 25,\n                            columnNumber: 13\n                        }, this)\n                    }, void 0, false, {\n                        fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/pages/_app.tsx\",\n                        lineNumber: 24,\n                        columnNumber: 11\n                    }, this)\n                }, void 0, false, {\n                    fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/pages/_app.tsx\",\n                    lineNumber: 23,\n                    columnNumber: 9\n                }, this)\n            }, void 0, false, {\n                fileName: \"/home/ubuntu/Desktop/quangnm/nlsql/wren-ui/src/pages/_app.tsx\",\n                lineNumber: 22,\n                columnNumber: 7\n            }, this)\n        ]\n    }, void 0, true);\n}\n/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (App);\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiLi9zcmMvcGFnZXMvX2FwcC50c3giLCJtYXBwaW5ncyI6Ijs7Ozs7Ozs7Ozs7Ozs7Ozs7OztBQUM2QjtBQUNEO0FBQ0s7QUFDVTtBQUNvQjtBQUNaO0FBQ0g7QUFDWTtBQUU1RFEsbUJBQU9BLENBQUM7QUFFUlAsa0VBQUlBLENBQUNRLG1CQUFtQixDQUFDRixxRUFBZ0JBO0FBRXpDLFNBQVNHLElBQUksRUFBRUMsU0FBUyxFQUFFQyxTQUFTLEVBQVk7SUFDN0MscUJBQ0U7OzBCQUNFLDhEQUFDWixrREFBSUE7O2tDQUNILDhEQUFDYTtrQ0FBTTs7Ozs7O2tDQUNQLDhEQUFDQzt3QkFBS0MsS0FBSTt3QkFBT0MsTUFBSzs7Ozs7Ozs7Ozs7OzBCQUV4Qiw4REFBQ1osd0VBQW9CQTswQkFDbkIsNEVBQUNFLDBEQUFjQTtvQkFBQ1csUUFBUWQsc0RBQVlBOzhCQUNsQyw0RUFBQ0UsNkRBQWVBO3dCQUFDWSxRQUFRZixtREFBT0E7a0NBQzlCLDRFQUFDZ0I7NEJBQUtDLFdBQVU7c0NBQ2QsNEVBQUNSO2dDQUFXLEdBQUdDLFNBQVM7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7QUFPdEM7QUFFQSxpRUFBZUYsR0FBR0EsRUFBQyIsInNvdXJjZXMiOlsid2VicGFjazovL3dyZW4tdWkvLi9zcmMvcGFnZXMvX2FwcC50c3g/ZjlkNiJdLCJzb3VyY2VzQ29udGVudCI6WyJpbXBvcnQgeyBBcHBQcm9wcyB9IGZyb20gJ25leHQvYXBwJztcbmltcG9ydCBIZWFkIGZyb20gJ25leHQvaGVhZCc7XG5pbXBvcnQgeyBTcGluIH0gZnJvbSAnYW50ZCc7XG5pbXBvcnQgcG9zdGhvZyBmcm9tICdwb3N0aG9nLWpzJztcbmltcG9ydCBhcG9sbG9DbGllbnQgZnJvbSAnQC9hcG9sbG8vY2xpZW50JztcbmltcG9ydCB7IEdsb2JhbENvbmZpZ1Byb3ZpZGVyIH0gZnJvbSAnQC9ob29rcy91c2VHbG9iYWxDb25maWcnO1xuaW1wb3J0IHsgUG9zdEhvZ1Byb3ZpZGVyIH0gZnJvbSAncG9zdGhvZy1qcy9yZWFjdCc7XG5pbXBvcnQgeyBBcG9sbG9Qcm92aWRlciB9IGZyb20gJ0BhcG9sbG8vY2xpZW50JztcbmltcG9ydCB7IGRlZmF1bHRJbmRpY2F0b3IgfSBmcm9tICdAL2NvbXBvbmVudHMvUGFnZUxvYWRpbmcnO1xuXG5yZXF1aXJlKCcuLi9zdHlsZXMvaW5kZXgubGVzcycpO1xuXG5TcGluLnNldERlZmF1bHRJbmRpY2F0b3IoZGVmYXVsdEluZGljYXRvcik7XG5cbmZ1bmN0aW9uIEFwcCh7IENvbXBvbmVudCwgcGFnZVByb3BzIH06IEFwcFByb3BzKSB7XG4gIHJldHVybiAoXG4gICAgPD5cbiAgICAgIDxIZWFkPlxuICAgICAgICA8dGl0bGU+UFRJVCBBSTwvdGl0bGU+XG4gICAgICAgIDxsaW5rIHJlbD1cImljb25cIiBocmVmPVwiL2Zhdmljb24uaWNvXCIgLz5cbiAgICAgIDwvSGVhZD5cbiAgICAgIDxHbG9iYWxDb25maWdQcm92aWRlcj5cbiAgICAgICAgPEFwb2xsb1Byb3ZpZGVyIGNsaWVudD17YXBvbGxvQ2xpZW50fT5cbiAgICAgICAgICA8UG9zdEhvZ1Byb3ZpZGVyIGNsaWVudD17cG9zdGhvZ30+XG4gICAgICAgICAgICA8bWFpbiBjbGFzc05hbWU9XCJhcHBcIj5cbiAgICAgICAgICAgICAgPENvbXBvbmVudCB7Li4ucGFnZVByb3BzfSAvPlxuICAgICAgICAgICAgPC9tYWluPlxuICAgICAgICAgIDwvUG9zdEhvZ1Byb3ZpZGVyPlxuICAgICAgICA8L0Fwb2xsb1Byb3ZpZGVyPlxuICAgICAgPC9HbG9iYWxDb25maWdQcm92aWRlcj5cbiAgICA8Lz5cbiAgKTtcbn1cblxuZXhwb3J0IGRlZmF1bHQgQXBwO1xuIl0sIm5hbWVzIjpbIkhlYWQiLCJTcGluIiwicG9zdGhvZyIsImFwb2xsb0NsaWVudCIsIkdsb2JhbENvbmZpZ1Byb3ZpZGVyIiwiUG9zdEhvZ1Byb3ZpZGVyIiwiQXBvbGxvUHJvdmlkZXIiLCJkZWZhdWx0SW5kaWNhdG9yIiwicmVxdWlyZSIsInNldERlZmF1bHRJbmRpY2F0b3IiLCJBcHAiLCJDb21wb25lbnQiLCJwYWdlUHJvcHMiLCJ0aXRsZSIsImxpbmsiLCJyZWwiLCJocmVmIiwiY2xpZW50IiwibWFpbiIsImNsYXNzTmFtZSJdLCJzb3VyY2VSb290IjoiIn0=\n//# sourceURL=webpack-internal:///./src/pages/_app.tsx\n");

/***/ }),

/***/ "./src/utils/env.ts":
/*!**************************!*\
  !*** ./src/utils/env.ts ***!
  \**************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"default\": () => (__WEBPACK_DEFAULT_EXPORT__),\n/* harmony export */   getUserConfig: () => (/* binding */ getUserConfig)\n/* harmony export */ });\nconst env = {\n    isDevelopment: \"development\" === \"development\",\n    isProduction: \"development\" === \"production\"\n};\n/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (env);\n// Get the user configuration\nconst getUserConfig = async ()=>{\n    const config = await fetch(\"/api/config\").then((res)=>res.json());\n    const decodedTelemetryKey = Buffer.from(config.telemetryKey, \"base64\").toString();\n    return {\n        ...config,\n        telemetryKey: decodedTelemetryKey\n    };\n};\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiLi9zcmMvdXRpbHMvZW52LnRzIiwibWFwcGluZ3MiOiI7Ozs7O0FBQUEsTUFBTUEsTUFBTTtJQUNWQyxlQUFlQyxrQkFBeUI7SUFDeENDLGNBQWNELGtCQUF5QjtBQUN6QztBQUVBLGlFQUFlRixHQUFHQSxFQUFDO0FBU25CLDZCQUE2QjtBQUN0QixNQUFNSSxnQkFBZ0I7SUFDM0IsTUFBTUMsU0FBUyxNQUFNQyxNQUFNLGVBQWVDLElBQUksQ0FBQyxDQUFDQyxNQUFRQSxJQUFJQyxJQUFJO0lBQ2hFLE1BQU1DLHNCQUFzQkMsT0FBT0MsSUFBSSxDQUNyQ1AsT0FBT1EsWUFBWSxFQUNuQixVQUNBQyxRQUFRO0lBQ1YsT0FBTztRQUFFLEdBQUdULE1BQU07UUFBRVEsY0FBY0g7SUFBb0I7QUFDeEQsRUFBRSIsInNvdXJjZXMiOlsid2VicGFjazovL3dyZW4tdWkvLi9zcmMvdXRpbHMvZW52LnRzP2NiZTgiXSwic291cmNlc0NvbnRlbnQiOlsiY29uc3QgZW52ID0ge1xuICBpc0RldmVsb3BtZW50OiBwcm9jZXNzLmVudi5OT0RFX0VOViA9PT0gJ2RldmVsb3BtZW50JyxcbiAgaXNQcm9kdWN0aW9uOiBwcm9jZXNzLmVudi5OT0RFX0VOViA9PT0gJ3Byb2R1Y3Rpb24nLFxufTtcblxuZXhwb3J0IGRlZmF1bHQgZW52O1xuXG5leHBvcnQgdHlwZSBVc2VyQ29uZmlnID0ge1xuICBpc1RlbGVtZXRyeUVuYWJsZWQ6IGJvb2xlYW47XG4gIHRlbGVtZXRyeUtleTogc3RyaW5nO1xuICB0ZWxlbWV0cnlIb3N0OiBzdHJpbmc7XG4gIHVzZXJVVUlEOiBzdHJpbmc7XG59O1xuXG4vLyBHZXQgdGhlIHVzZXIgY29uZmlndXJhdGlvblxuZXhwb3J0IGNvbnN0IGdldFVzZXJDb25maWcgPSBhc3luYyAoKTogUHJvbWlzZTxVc2VyQ29uZmlnPiA9PiB7XG4gIGNvbnN0IGNvbmZpZyA9IGF3YWl0IGZldGNoKCcvYXBpL2NvbmZpZycpLnRoZW4oKHJlcykgPT4gcmVzLmpzb24oKSk7XG4gIGNvbnN0IGRlY29kZWRUZWxlbWV0cnlLZXkgPSBCdWZmZXIuZnJvbShcbiAgICBjb25maWcudGVsZW1ldHJ5S2V5LFxuICAgICdiYXNlNjQnLFxuICApLnRvU3RyaW5nKCk7XG4gIHJldHVybiB7IC4uLmNvbmZpZywgdGVsZW1ldHJ5S2V5OiBkZWNvZGVkVGVsZW1ldHJ5S2V5IH07XG59O1xuIl0sIm5hbWVzIjpbImVudiIsImlzRGV2ZWxvcG1lbnQiLCJwcm9jZXNzIiwiaXNQcm9kdWN0aW9uIiwiZ2V0VXNlckNvbmZpZyIsImNvbmZpZyIsImZldGNoIiwidGhlbiIsInJlcyIsImpzb24iLCJkZWNvZGVkVGVsZW1ldHJ5S2V5IiwiQnVmZmVyIiwiZnJvbSIsInRlbGVtZXRyeUtleSIsInRvU3RyaW5nIl0sInNvdXJjZVJvb3QiOiIifQ==\n//# sourceURL=webpack-internal:///./src/utils/env.ts\n");

/***/ }),

/***/ "./src/utils/errorHandler.tsx":
/*!************************************!*\
  !*** ./src/utils/errorHandler.tsx ***!
  \************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   ERROR_CODES: () => (/* binding */ ERROR_CODES),\n/* harmony export */   \"default\": () => (__WEBPACK_DEFAULT_EXPORT__),\n/* harmony export */   parseGraphQLError: () => (/* binding */ parseGraphQLError)\n/* harmony export */ });\n/* harmony import */ var _barrel_optimize_names_message_antd__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! __barrel_optimize__?names=message!=!antd */ \"__barrel_optimize__?names=message!=!./src/import/antd.ts\");\n\n// Refer to backend GeneralErrorCodes for mapping\nconst ERROR_CODES = {\n    INVALID_CALCULATED_FIELD: \"INVALID_CALCULATED_FIELD\",\n    CONNECTION_REFUSED: \"CONNECTION_REFUSED\",\n    NO_CHART: \"NO_CHART\"\n};\n/**\n * Replace the token %{s} in the message with the detail message.\n * For example:\n *\n *  Input: ('Failed to update %{data source}.')\n *  Output: Failed to update data source.\n *\n *  Input: ('Failed to update %{data source}.', 'The data source is not found.')\n *  Output: Failed to update - The data source is not found.\n *\n * @param message The default message with replace token %{s}.\n * @param detailMessage The detail message.\n * @returns string\n */ const replaceMessage = (message, detailMessage)=>{\n    const regex = /\\%\\{.+\\}/;\n    const textWithoutTokenRegex = /(?<=\\%\\{).+(?=\\})/;\n    const matchText = message.match(textWithoutTokenRegex);\n    if (matchText === null) {\n        console.warn(\"Replace token not found in message:\", message);\n        return message;\n    }\n    return detailMessage ? message.replace(regex, `- ${detailMessage}`) : message.replace(regex, matchText[0]);\n};\nclass ErrorHandler {\n    handle(error) {\n        const errorMessage = this.getErrorMessage(error);\n        if (errorMessage) _barrel_optimize_names_message_antd__WEBPACK_IMPORTED_MODULE_0__.message.error(errorMessage);\n    }\n}\nconst errorHandlers = new Map();\nclass SaveTablesErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to create model(s).\";\n        }\n    }\n}\nclass SaveRelationsErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to define relations.\";\n        }\n    }\n}\nclass CreateAskingTaskErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to create asking task.\";\n        }\n    }\n}\nclass CreateThreadErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to create thread.\";\n        }\n    }\n}\nclass UpdateThreadErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to update thread.\";\n        }\n    }\n}\nclass DeleteThreadErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to delete thread.\";\n        }\n    }\n}\nclass CreateThreadResponseErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to create thread response.\";\n        }\n    }\n}\nclass UpdateThreadResponseErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to update thread response.\";\n        }\n    }\n}\nclass GenerateThreadResponseAnswerErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to generate thread response answer.\";\n        }\n    }\n}\nclass AdjustThreadResponseErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to adjust thread response answer.\";\n        }\n    }\n}\nclass CreateViewErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to create view.\";\n        }\n    }\n}\nclass UpdateDataSourceErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return replaceMessage(`Failed to update %{data source}.`, error.message);\n        }\n    }\n}\nclass CreateModelErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to create model.\";\n        }\n    }\n}\nclass UpdateModelErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to update model.\";\n        }\n    }\n}\nclass DeleteModelErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to delete model.\";\n        }\n    }\n}\nclass UpdateModelMetadataErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to update model metadata.\";\n        }\n    }\n}\nclass CreateCalculatedFieldErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to create calculated field.\";\n        }\n    }\n}\nclass UpdateCalculatedFieldErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to update calculated field.\";\n        }\n    }\n}\nclass DeleteCalculatedFieldErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to delete calculated field.\";\n        }\n    }\n}\nclass CreateRelationshipErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to create relationship.\";\n        }\n    }\n}\nclass UpdateRelationshipErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to update relationship.\";\n        }\n    }\n}\nclass DeleteRelationshipErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to delete relationship.\";\n        }\n    }\n}\nclass UpdateViewMetadataErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to update view metadata.\";\n        }\n    }\n}\nclass TriggerDataSourceDetectionErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to scan data source.\";\n        }\n    }\n}\nclass ResolveSchemaChangeErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to resolve schema change.\";\n        }\n    }\n}\nclass CreateDashboardItemErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to create dashboard item.\";\n        }\n    }\n}\nclass UpdateDashboardItemErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to update dashboard item.\";\n        }\n    }\n}\nclass UpdateDashboardItemLayoutsErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to update dashboard item layouts.\";\n        }\n    }\n}\nclass DeleteDashboardItemErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to delete dashboard item.\";\n        }\n    }\n}\nclass SetDashboardScheduleErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to set dashboard schedule.\";\n        }\n    }\n}\nclass CreateSqlPairErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to create question-sql pair.\";\n        }\n    }\n}\nclass UpdateSqlPairErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to update question-sql pair.\";\n        }\n    }\n}\nclass DeleteSqlPairErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to delete question-sql pair.\";\n        }\n    }\n}\nclass CreateInstructionErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to create instruction.\";\n        }\n    }\n}\nclass UpdateInstructionErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to update instruction.\";\n        }\n    }\n}\nclass DeleteInstructionErrorHandler extends ErrorHandler {\n    getErrorMessage(error) {\n        switch(error.extensions?.code){\n            default:\n                return \"Failed to delete instruction.\";\n        }\n    }\n}\nerrorHandlers.set(\"SaveTables\", new SaveTablesErrorHandler());\nerrorHandlers.set(\"SaveRelations\", new SaveRelationsErrorHandler());\nerrorHandlers.set(\"CreateAskingTask\", new CreateAskingTaskErrorHandler());\nerrorHandlers.set(\"CreateThread\", new CreateThreadErrorHandler());\nerrorHandlers.set(\"UpdateThread\", new UpdateThreadErrorHandler());\nerrorHandlers.set(\"DeleteThread\", new DeleteThreadErrorHandler());\nerrorHandlers.set(\"CreateThreadResponse\", new CreateThreadResponseErrorHandler());\nerrorHandlers.set(\"UpdateThreadResponse\", new UpdateThreadResponseErrorHandler());\nerrorHandlers.set(\"GenerateThreadResponseAnswer\", new GenerateThreadResponseAnswerErrorHandler());\nerrorHandlers.set(\"AdjustThreadResponse\", new AdjustThreadResponseErrorHandler());\nerrorHandlers.set(\"CreateView\", new CreateViewErrorHandler());\nerrorHandlers.set(\"UpdateDataSource\", new UpdateDataSourceErrorHandler());\nerrorHandlers.set(\"CreateModel\", new CreateModelErrorHandler());\nerrorHandlers.set(\"UpdateModel\", new UpdateModelErrorHandler());\nerrorHandlers.set(\"DeleteModel\", new DeleteModelErrorHandler());\nerrorHandlers.set(\"UpdateModelMetadata\", new UpdateModelMetadataErrorHandler());\nerrorHandlers.set(\"UpdateViewMetadata\", new UpdateViewMetadataErrorHandler());\nerrorHandlers.set(\"CreateCalculatedField\", new CreateCalculatedFieldErrorHandler());\nerrorHandlers.set(\"UpdateCalculatedField\", new UpdateCalculatedFieldErrorHandler());\nerrorHandlers.set(\"DeleteCalculatedField\", new DeleteCalculatedFieldErrorHandler());\n// Relationship\nerrorHandlers.set(\"CreateRelationship\", new CreateRelationshipErrorHandler());\nerrorHandlers.set(\"UpdateRelationship\", new UpdateRelationshipErrorHandler());\nerrorHandlers.set(\"DeleteRelationship\", new DeleteRelationshipErrorHandler());\n// Schema change\nerrorHandlers.set(\"TriggerDataSourceDetection\", new TriggerDataSourceDetectionErrorHandler());\nerrorHandlers.set(\"ResolveSchemaChange\", new ResolveSchemaChangeErrorHandler());\n// Dashboard\nerrorHandlers.set(\"CreateDashboardItem\", new CreateDashboardItemErrorHandler());\nerrorHandlers.set(\"UpdateDashboardItem\", new UpdateDashboardItemErrorHandler());\nerrorHandlers.set(\"UpdateDashboardItemLayouts\", new UpdateDashboardItemLayoutsErrorHandler());\nerrorHandlers.set(\"DeleteDashboardItem\", new DeleteDashboardItemErrorHandler());\nerrorHandlers.set(\"SetDashboardSchedule\", new SetDashboardScheduleErrorHandler());\n// SQL Pair\nerrorHandlers.set(\"CreateSqlPair\", new CreateSqlPairErrorHandler());\nerrorHandlers.set(\"UpdateSqlPair\", new UpdateSqlPairErrorHandler());\nerrorHandlers.set(\"DeleteSqlPair\", new DeleteSqlPairErrorHandler());\n// Instruction\nerrorHandlers.set(\"CreateInstruction\", new CreateInstructionErrorHandler());\nerrorHandlers.set(\"UpdateInstruction\", new UpdateInstructionErrorHandler());\nerrorHandlers.set(\"DeleteInstruction\", new DeleteInstructionErrorHandler());\nconst errorHandler = (error)=>{\n    // networkError\n    if (error.networkError) {\n        _barrel_optimize_names_message_antd__WEBPACK_IMPORTED_MODULE_0__.message.error(\"No internet. Please check your network connection and try again.\");\n    }\n    const operationName = error?.operation?.operationName || \"\";\n    if (error.graphQLErrors) {\n        for (const err of error.graphQLErrors){\n            errorHandlers.get(operationName)?.handle(err);\n        }\n    }\n};\n/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (errorHandler);\nconst parseGraphQLError = (error)=>{\n    if (!error) return null;\n    const graphQLErrors = error.graphQLErrors?.[0];\n    const extensions = graphQLErrors?.extensions || {};\n    return {\n        message: extensions.message,\n        shortMessage: extensions.shortMessage,\n        code: extensions.code,\n        stacktrace: extensions?.stacktrace\n    };\n};\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,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RCxhQUFhLEVBQUUsQ0FBQyxFQUFFO0lBQzVELE1BQU0xQyxhQUFhMEMsZUFBZTFDLGNBQWMsQ0FBQztJQUNqRCxPQUFPO1FBQ0x0QixTQUFTc0IsV0FBV3RCLE9BQU87UUFDM0JvRSxjQUFjOUMsV0FBVzhDLFlBQVk7UUFDckM3QyxNQUFNRCxXQUFXQyxJQUFJO1FBQ3JCOEMsWUFBWS9DLFlBQVkrQztJQUMxQjtBQUNGLEVBQUUiLCJzb3VyY2VzIjpbIndlYnBhY2s6Ly93cmVuLXVpLy4vc3JjL3V0aWxzL2Vycm9ySGFuZGxlci50c3g/YzBiYyJdLCJzb3VyY2VzQ29udGVudCI6WyJpbXBvcnQgeyBHcmFwaFFMRXJyb3IgfSBmcm9tICdncmFwaHFsJztcbmltcG9ydCB7IEVycm9yUmVzcG9uc2UgfSBmcm9tICdAYXBvbGxvL2NsaWVudC9saW5rL2Vycm9yJztcbmltcG9ydCB7IEFwb2xsb0Vycm9yIH0gZnJvbSAnQGFwb2xsby9jbGllbnQnO1xuaW1wb3J0IHsgbWVzc2FnZSB9IGZyb20gJ2FudGQnO1xuXG4vLyBSZWZlciB0byBiYWNrZW5kIEdlbmVyYWxFcnJvckNvZGVzIGZvciBtYXBwaW5nXG5leHBvcnQgY29uc3QgRVJST1JfQ09ERVMgPSB7XG4gIElOVkFMSURfQ0FMQ1VMQVRFRF9GSUVMRDogJ0lOVkFMSURfQ0FMQ1VMQVRFRF9GSUVMRCcsXG4gIENPTk5FQ1RJT05fUkVGVVNFRDogJ0NPTk5FQ1RJT05fUkVGVVNFRCcsXG4gIE5PX0NIQVJUOiAnTk9fQ0hBUlQnLFxufTtcblxuLyoqXG4gKiBSZXBsYWNlIHRoZSB0b2tlbiAle3N9IGluIHRoZSBtZXNzYWdlIHdpdGggdGhlIGRldGFpbCBtZXNzYWdlLlxuICogRm9yIGV4YW1wbGU6XG4gKlxuICogIElucHV0OiAoJ0ZhaWxlZCB0byB1cGRhdGUgJXtkYXRhIHNvdXJjZX0uJylcbiAqICBPdXRwdXQ6IEZhaWxlZCB0byB1cGRhdGUgZGF0YSBzb3VyY2UuXG4gKlxuICogIElucHV0OiAoJ0ZhaWxlZCB0byB1cGRhdGUgJXtkYXRhIHNvdXJjZX0uJywgJ1RoZSBkYXRhIHNvdXJjZSBpcyBub3QgZm91bmQuJylcbiAqICBPdXRwdXQ6IEZhaWxlZCB0byB1cGRhdGUgLSBUaGUgZGF0YSBzb3VyY2UgaXMgbm90IGZvdW5kLlxuICpcbiAqIEBwYXJhbSBtZXNzYWdlIFRoZSBkZWZhdWx0IG1lc3NhZ2Ugd2l0aCByZXBsYWNlIHRva2VuICV7c30uXG4gKiBAcGFyYW0gZGV0YWlsTWVzc2FnZSBUaGUgZGV0YWlsIG1lc3NhZ2UuXG4gKiBAcmV0dXJucyBzdHJpbmdcbiAqL1xuY29uc3QgcmVwbGFjZU1lc3NhZ2UgPSAobWVzc2FnZTogc3RyaW5nLCBkZXRhaWxNZXNzYWdlPzogc3RyaW5nKSA9PiB7XG4gIGNvbnN0IHJlZ2V4ID0gL1xcJVxcey4rXFx9LztcbiAgY29uc3QgdGV4dFdpdGhvdXRUb2tlblJlZ2V4ID0gLyg/PD1cXCVcXHspLisoPz1cXH0pLztcbiAgY29uc3QgbWF0Y2hUZXh0ID0gbWVzc2FnZS5tYXRjaCh0ZXh0V2l0aG91dFRva2VuUmVnZXgpO1xuICBpZiAobWF0Y2hUZXh0ID09PSBudWxsKSB7XG4gICAgY29uc29sZS53YXJuKCdSZXBsYWNlIHRva2VuIG5vdCBmb3VuZCBpbiBtZXNzYWdlOicsIG1lc3NhZ2UpO1xuICAgIHJldHVybiBtZXNzYWdlO1xuICB9XG4gIHJldHVybiBkZXRhaWxNZXNzYWdlXG4gICAgPyBtZXNzYWdlLnJlcGxhY2UocmVnZXgsIGAtICR7ZGV0YWlsTWVzc2FnZX1gKVxuICAgIDogbWVzc2FnZS5yZXBsYWNlKHJlZ2V4LCBtYXRjaFRleHRbMF0pO1xufTtcblxuYWJzdHJhY3QgY2xhc3MgRXJyb3JIYW5kbGVyIHtcbiAgcHVibGljIGhhbmRsZShlcnJvcjogR3JhcGhRTEVycm9yKSB7XG4gICAgY29uc3QgZXJyb3JNZXNzYWdlID0gdGhpcy5nZXRFcnJvck1lc3NhZ2UoZXJyb3IpO1xuICAgIGlmIChlcnJvck1lc3NhZ2UpIG1lc3NhZ2UuZXJyb3IoZXJyb3JNZXNzYWdlKTtcbiAgfVxuXG4gIGFic3RyYWN0IGdldEVycm9yTWVzc2FnZShlcnJvcjogR3JhcGhRTEVycm9yKTogc3RyaW5nIHwgbnVsbDtcbn1cblxuY29uc3QgZXJyb3JIYW5kbGVycyA9IG5ldyBNYXA8c3RyaW5nLCBFcnJvckhhbmRsZXI+KCk7XG5cbmNsYXNzIFNhdmVUYWJsZXNFcnJvckhhbmRsZXIgZXh0ZW5kcyBFcnJvckhhbmRsZXIge1xuICBwdWJsaWMgZ2V0RXJyb3JNZXNzYWdlKGVycm9yOiBHcmFwaFFMRXJyb3IpIHtcbiAgICBzd2l0Y2ggKGVycm9yLmV4dGVuc2lvbnM/LmNvZGUpIHtcbiAgICAgIGRlZmF1bHQ6XG4gICAgICAgIHJldHVybiAnRmFpbGVkIHRvIGNyZWF0ZSBtb2RlbChzKS4nO1xuICAgIH1cbiAgfVxufVxuXG5jbGFzcyBTYXZlUmVsYXRpb25zRXJyb3JIYW5kbGVyIGV4dGVuZHMgRXJyb3JIYW5kbGVyIHtcbiAgcHVibGljIGdldEVycm9yTWVzc2FnZShlcnJvcjogR3JhcGhRTEVycm9yKSB7XG4gICAgc3dpdGNoIChlcnJvci5leHRlbnNpb25zPy5jb2RlKSB7XG4gICAgICBkZWZhdWx0OlxuICAgICAgICByZXR1cm4gJ0ZhaWxlZCB0byBkZWZpbmUgcmVsYXRpb25zLic7XG4gICAgfVxuICB9XG59XG5cbmNsYXNzIENyZWF0ZUFza2luZ1Rhc2tFcnJvckhhbmRsZXIgZXh0ZW5kcyBFcnJvckhhbmRsZXIge1xuICBwdWJsaWMgZ2V0RXJyb3JNZXNzYWdlKGVycm9yOiBHcmFwaFFMRXJyb3IpIHtcbiAgICBzd2l0Y2ggKGVycm9yLmV4dGVuc2lvbnM/LmNvZGUpIHtcbiAgICAgIGRlZmF1bHQ6XG4gICAgICAgIHJldHVybiAnRmFpbGVkIHRvIGNyZWF0ZSBhc2tpbmcgdGFzay4nO1xuICAgIH1cbiAgfVxufVxuXG5jbGFzcyBDcmVhdGVUaHJlYWRFcnJvckhhbmRsZXIgZXh0ZW5kcyBFcnJvckhhbmRsZXIge1xuICBwdWJsaWMgZ2V0RXJyb3JNZXNzYWdlKGVycm9yOiBHcmFwaFFMRXJyb3IpIHtcbiAgICBzd2l0Y2ggKGVycm9yLmV4dGVuc2lvbnM/LmNvZGUpIHtcbiAgICAgIGRlZmF1bHQ6XG4gICAgICAgIHJldHVybiAnRmFpbGVkIHRvIGNyZWF0ZSB0aHJlYWQuJztcbiAgICB9XG4gIH1cbn1cblxuY2xhc3MgVXBkYXRlVGhyZWFkRXJyb3JIYW5kbGVyIGV4dGVuZHMgRXJyb3JIYW5kbGVyIHtcbiAgcHVibGljIGdldEVycm9yTWVzc2FnZShlcnJvcjogR3JhcGhRTEVycm9yKSB7XG4gICAgc3dpdGNoIChlcnJvci5leHRlbnNpb25zPy5jb2RlKSB7XG4gICAgICBkZWZhdWx0OlxuICAgICAgICByZXR1cm4gJ0ZhaWxlZCB0byB1cGRhdGUgdGhyZWFkLic7XG4gICAgfVxuICB9XG59XG5cbmNsYXNzIERlbGV0ZVRocmVhZEVycm9ySGFuZGxlciBleHRlbmRzIEVycm9ySGFuZGxlciB7XG4gIHB1YmxpYyBnZXRFcnJvck1lc3NhZ2UoZXJyb3I6IEdyYXBoUUxFcnJvcikge1xuICAgIHN3aXRjaCAoZXJyb3IuZXh0ZW5zaW9ucz8uY29kZSkge1xuICAgICAgZGVmYXVsdDpcbiAgICAgICAgcmV0dXJuICdGYWlsZWQgdG8gZGVsZXRlIHRocmVhZC4nO1xuICAgIH1cbiAgfVxufVxuXG5jbGFzcyBDcmVhdGVUaHJlYWRSZXNwb25zZUVycm9ySGFuZGxlciBleHRlbmRzIEVycm9ySGFuZGxlciB7XG4gIHB1YmxpYyBnZXRFcnJvck1lc3NhZ2UoZXJyb3I6IEdyYXBoUUxFcnJvcikge1xuICAgIHN3aXRjaCAoZXJyb3IuZXh0ZW5zaW9ucz8uY29kZSkge1xuICAgICAgZGVmYXVsdDpcbiAgICAgICAgcmV0dXJuICdGYWlsZWQgdG8gY3JlYXRlIHRocmVhZCByZXNwb25zZS4nO1xuICAgIH1cbiAgfVxufVxuXG5jbGFzcyBVcGRhdGVUaHJlYWRSZXNwb25zZUVycm9ySGFuZGxlciBleHRlbmRzIEVycm9ySGFuZGxlciB7XG4gIHB1YmxpYyBnZXRFcnJvck1lc3NhZ2UoZXJyb3I6IEdyYXBoUUxFcnJvcikge1xuICAgIHN3aXRjaCAoZXJyb3IuZXh0ZW5zaW9ucz8uY29kZSkge1xuICAgICAgZGVmYXVsdDpcbiAgICAgICAgcmV0dXJuICdGYWlsZWQgdG8gdXBkYXRlIHRocmVhZCByZXNwb25zZS4nO1xuICAgIH1cbiAgfVxufVxuXG5jbGFzcyBHZW5lcmF0ZVRocmVhZFJlc3BvbnNlQW5zd2VyRXJyb3JIYW5kbGVyIGV4dGVuZHMgRXJyb3JIYW5kbGVyIHtcbiAgcHVibGljIGdldEVycm9yTWVzc2FnZShlcnJvcjogR3JhcGhRTEVycm9yKSB7XG4gICAgc3dpdGNoIChlcnJvci5leHRlbnNpb25zPy5jb2RlKSB7XG4gICAgICBkZWZhdWx0OlxuICAgICAgICByZXR1cm4gJ0ZhaWxlZCB0byBnZW5lcmF0ZSB0aHJlYWQgcmVzcG9uc2UgYW5zd2VyLic7XG4gICAgfVxuICB9XG59XG5cbmNsYXNzIEFkanVzdFRocmVhZFJlc3BvbnNlRXJyb3JIYW5kbGVyIGV4dGVuZHMgRXJyb3JIYW5kbGVyIHtcbiAgcHVibGljIGdldEVycm9yTWVzc2FnZShlcnJvcjogR3JhcGhRTEVycm9yKSB7XG4gICAgc3dpdGNoIChlcnJvci5leHRlbnNpb25zPy5jb2RlKSB7XG4gICAgICBkZWZhdWx0OlxuICAgICAgICByZXR1cm4gJ0ZhaWxlZCB0byBhZGp1c3QgdGhyZWFkIHJlc3BvbnNlIGFuc3dlci4nO1xuICAgIH1cbiAgfVxufVxuXG5jbGFzcyBDcmVhdGVWaWV3RXJyb3JIYW5kbGVyIGV4dGVuZHMgRXJyb3JIYW5kbGVyIHtcbiAgcHVibGljIGdldEVycm9yTWVzc2FnZShlcnJvcjogR3JhcGhRTEVycm9yKSB7XG4gICAgc3dpdGNoIChlcnJvci5leHRlbnNpb25zPy5jb2RlKSB7XG4gICAgICBkZWZhdWx0OlxuICAgICAgICByZXR1cm4gJ0ZhaWxlZCB0byBjcmVhdGUgdmlldy4nO1xuICAgIH1cbiAgfVxufVxuXG5jbGFzcyBVcGRhdGVEYXRhU291cmNlRXJyb3JIYW5kbGVyIGV4dGVuZHMgRXJyb3JIYW5kbGVyIHtcbiAgcHVibGljIGdldEVycm9yTWVzc2FnZShlcnJvcjogR3JhcGhRTEVycm9yKSB7XG4gICAgc3dpdGNoIChlcnJvci5leHRlbnNpb25zPy5jb2RlKSB7XG4gICAgICBkZWZhdWx0OlxuICAgICAgICByZXR1cm4gcmVwbGFjZU1lc3NhZ2UoXG4gICAgICAgICAgYEZhaWxlZCB0byB1cGRhdGUgJXtkYXRhIHNvdXJjZX0uYCxcbiAgICAgICAgICBlcnJvci5tZXNzYWdlLFxuICAgICAgICApO1xuICAgIH1cbiAgfVxufVxuXG5jbGFzcyBDcmVhdGVNb2RlbEVycm9ySGFuZGxlciBleHRlbmRzIEVycm9ySGFuZGxlciB7XG4gIHB1YmxpYyBnZXRFcnJvck1lc3NhZ2UoZXJyb3I6IEdyYXBoUUxFcnJvcikge1xuICAgIHN3aXRjaCAoZXJyb3IuZXh0ZW5zaW9ucz8uY29kZSkge1xuICAgICAgZGVmYXVsdDpcbiAgICAgICAgcmV0dXJuICdGYWlsZWQgdG8gY3JlYXRlIG1vZGVsLic7XG4gICAgfVxuICB9XG59XG5cbmNsYXNzIFVwZGF0ZU1vZGVsRXJyb3JIYW5kbGVyIGV4dGVuZHMgRXJyb3JIYW5kbGVyIHtcbiAgcHVibGljIGdldEVycm9yTWVzc2FnZShlcnJvcjogR3JhcGhRTEVycm9yKSB7XG4gICAgc3dpdGNoIChlcnJvci5leHRlbnNpb25zPy5jb2RlKSB7XG4gICAgICBkZWZhdWx0OlxuICAgICAgICByZXR1cm4gJ0ZhaWxlZCB0byB1cGRhdGUgbW9kZWwuJztcbiAgICB9XG4gIH1cbn1cblxuY2xhc3MgRGVsZXRlTW9kZWxFcnJvckhhbmRsZXIgZXh0ZW5kcyBFcnJvckhhbmRsZXIge1xuICBwdWJsaWMgZ2V0RXJyb3JNZXNzYWdlKGVycm9yOiBHcmFwaFFMRXJyb3IpIHtcbiAgICBzd2l0Y2ggKGVycm9yLmV4dGVuc2lvbnM/LmNvZGUpIHtcbiAgICAgIGRlZmF1bHQ6XG4gICAgICAgIHJldHVybiAnRmFpbGVkIHRvIGRlbGV0ZSBtb2RlbC4nO1xuICAgIH1cbiAgfVxufVxuXG5jbGFzcyBVcGRhdGVNb2RlbE1ldGFkYXRhRXJyb3JIYW5kbGVyIGV4dGVuZHMgRXJyb3JIYW5kbGVyIHtcbiAgcHVibGljIGdldEVycm9yTWVzc2FnZShlcnJvcjogR3JhcGhRTEVycm9yKSB7XG4gICAgc3dpdGNoIChlcnJvci5leHRlbnNpb25zPy5jb2RlKSB7XG4gICAgICBkZWZhdWx0OlxuICAgICAgICByZXR1cm4gJ0ZhaWxlZCB0byB1cGRhdGUgbW9kZWwgbWV0YWRhdGEuJztcbiAgICB9XG4gIH1cbn1cblxuY2xhc3MgQ3JlYXRlQ2FsY3VsYXRlZEZpZWxkRXJyb3JIYW5kbGVyIGV4dGVuZHMgRXJyb3JIYW5kbGVyIHtcbiAgcHVibGljIGdldEVycm9yTWVzc2FnZShlcnJvcjogR3JhcGhRTEVycm9yKSB7XG4gICAgc3dpdGNoIChlcnJvci5leHRlbnNpb25zPy5jb2RlKSB7XG4gICAgICBkZWZhdWx0OlxuICAgICAgICByZXR1cm4gJ0ZhaWxlZCB0byBjcmVhdGUgY2FsY3VsYXRlZCBmaWVsZC4nO1xuICAgIH1cbiAgfVxufVxuXG5jbGFzcyBVcGRhdGVDYWxjdWxhdGVkRmllbGRFcnJvckhhbmRsZXIgZXh0ZW5kcyBFcnJvckhhbmRsZXIge1xuICBwdWJsaWMgZ2V0RXJyb3JNZXNzYWdlKGVycm9yOiBHcmFwaFFMRXJyb3IpIHtcbiAgICBzd2l0Y2ggKGVycm9yLmV4dGVuc2lvbnM/LmNvZGUpIHtcbiAgICAgIGRlZmF1bHQ6XG4gICAgICAgIHJldHVybiAnRmFpbGVkIHRvIHVwZGF0ZSBjYWxjdWxhdGVkIGZpZWxkLic7XG4gICAgfVxuICB9XG59XG5cbmNsYXNzIERlbGV0ZUNhbGN1bGF0ZWRGaWVsZEVycm9ySGFuZGxlciBleHRlbmRzIEVycm9ySGFuZGxlciB7XG4gIHB1YmxpYyBnZXRFcnJvck1lc3NhZ2UoZXJyb3I6IEdyYXBoUUxFcnJvcikge1xuICAgIHN3aXRjaCAoZXJyb3IuZXh0ZW5zaW9ucz8uY29kZSkge1xuICAgICAgZGVmYXVsdDpcbiAgICAgICAgcmV0dXJuICdGYWlsZWQgdG8gZGVsZXRlIGNhbGN1bGF0ZWQgZmllbGQuJztcbiAgICB9XG4gIH1cbn1cblxuY2xhc3MgQ3JlYXRlUmVsYXRpb25zaGlwRXJyb3JIYW5kbGVyIGV4dGVuZHMgRXJyb3JIYW5kbGVyIHtcbiAgcHVibGljIGdldEVycm9yTWVzc2FnZShlcnJvcjogR3JhcGhRTEVycm9yKSB7XG4gICAgc3dpdGNoIChlcnJvci5leHRlbnNpb25zPy5jb2RlKSB7XG4gICAgICBkZWZhdWx0OlxuICAgICAgICByZXR1cm4gJ0ZhaWxlZCB0byBjcmVhdGUgcmVsYXRpb25zaGlwLic7XG4gICAgfVxuICB9XG59XG5cbmNsYXNzIFVwZGF0ZVJlbGF0aW9uc2hpcEVycm9ySGFuZGxlciBleHRlbmRzIEVycm9ySGFuZGxlciB7XG4gIHB1YmxpYyBnZXRFcnJvck1lc3NhZ2UoZXJyb3I6IEdyYXBoUUxFcnJvcikge1xuICAgIHN3aXRjaCAoZXJyb3IuZXh0ZW5zaW9ucz8uY29kZSkge1xuICAgICAgZGVmYXVsdDpcbiAgICAgICAgcmV0dXJuICdGYWlsZWQgdG8gdXBkYXRlIHJlbGF0aW9uc2hpcC4nO1xuICAgIH1cbiAgfVxufVxuXG5jbGFzcyBEZWxldGVSZWxhdGlvbnNoaXBFcnJvckhhbmRsZXIgZXh0ZW5kcyBFcnJvckhhbmRsZXIge1xuICBwdWJsaWMgZ2V0RXJyb3JNZXNzYWdlKGVycm9yOiBHcmFwaFFMRXJyb3IpIHtcbiAgICBzd2l0Y2ggKGVycm9yLmV4dGVuc2lvbnM/LmNvZGUpIHtcbiAgICAgIGRlZmF1bHQ6XG4gICAgICAgIHJldHVybiAnRmFpbGVkIHRvIGRlbGV0ZSByZWxhdGlvbnNoaXAuJztcbiAgICB9XG4gIH1cbn1cblxuY2xhc3MgVXBkYXRlVmlld01ldGFkYXRhRXJyb3JIYW5kbGVyIGV4dGVuZHMgRXJyb3JIYW5kbGVyIHtcbiAgcHVibGljIGdldEVycm9yTWVzc2FnZShlcnJvcjogR3JhcGhRTEVycm9yKSB7XG4gICAgc3dpdGNoIChlcnJvci5leHRlbnNpb25zPy5jb2RlKSB7XG4gICAgICBkZWZhdWx0OlxuICAgICAgICByZXR1cm4gJ0ZhaWxlZCB0byB1cGRhdGUgdmlldyBtZXRhZGF0YS4nO1xuICAgIH1cbiAgfVxufVxuXG5jbGFzcyBUcmlnZ2VyRGF0YVNvdXJjZURldGVjdGlvbkVycm9ySGFuZGxlciBleHRlbmRzIEVycm9ySGFuZGxlciB7XG4gIHB1YmxpYyBnZXRFcnJvck1lc3NhZ2UoZXJyb3I6IEdyYXBoUUxFcnJvcikge1xuICAgIHN3aXRjaCAoZXJyb3IuZXh0ZW5zaW9ucz8uY29kZSkge1xuICAgICAgZGVmYXVsdDpcbiAgICAgICAgcmV0dXJuICdGYWlsZWQgdG8gc2NhbiBkYXRhIHNvdXJjZS4nO1xuICAgIH1cbiAgfVxufVxuXG5jbGFzcyBSZXNvbHZlU2NoZW1hQ2hhbmdlRXJyb3JIYW5kbGVyIGV4dGVuZHMgRXJyb3JIYW5kbGVyIHtcbiAgcHVibGljIGdldEVycm9yTWVzc2FnZShlcnJvcjogR3JhcGhRTEVycm9yKSB7XG4gICAgc3dpdGNoIChlcnJvci5leHRlbnNpb25zPy5jb2RlKSB7XG4gICAgICBkZWZhdWx0OlxuICAgICAgICByZXR1cm4gJ0ZhaWxlZCB0byByZXNvbHZlIHNjaGVtYSBjaGFuZ2UuJztcbiAgICB9XG4gIH1cbn1cblxuY2xhc3MgQ3JlYXRlRGFzaGJvYXJkSXRlbUVycm9ySGFuZGxlciBleHRlbmRzIEVycm9ySGFuZGxlciB7XG4gIHB1YmxpYyBnZXRFcnJvck1lc3NhZ2UoZXJyb3I6IEdyYXBoUUxFcnJvcikge1xuICAgIHN3aXRjaCAoZXJyb3IuZXh0ZW5zaW9ucz8uY29kZSkge1xuICAgICAgZGVmYXVsdDpcbiAgICAgICAgcmV0dXJuICdGYWlsZWQgdG8gY3JlYXRlIGRhc2hib2FyZCBpdGVtLic7XG4gICAgfVxuICB9XG59XG5cbmNsYXNzIFVwZGF0ZURhc2hib2FyZEl0ZW1FcnJvckhhbmRsZXIgZXh0ZW5kcyBFcnJvckhhbmRsZXIge1xuICBwdWJsaWMgZ2V0RXJyb3JNZXNzYWdlKGVycm9yOiBHcmFwaFFMRXJyb3IpIHtcbiAgICBzd2l0Y2ggKGVycm9yLmV4dGVuc2lvbnM/LmNvZGUpIHtcbiAgICAgIGRlZmF1bHQ6XG4gICAgICAgIHJldHVybiAnRmFpbGVkIHRvIHVwZGF0ZSBkYXNoYm9hcmQgaXRlbS4nO1xuICAgIH1cbiAgfVxufVxuXG5jbGFzcyBVcGRhdGVEYXNoYm9hcmRJdGVtTGF5b3V0c0Vycm9ySGFuZGxlciBleHRlbmRzIEVycm9ySGFuZGxlciB7XG4gIHB1YmxpYyBnZXRFcnJvck1lc3NhZ2UoZXJyb3I6IEdyYXBoUUxFcnJvcikge1xuICAgIHN3aXRjaCAoZXJyb3IuZXh0ZW5zaW9ucz8uY29kZSkge1xuICAgICAgZGVmYXVsdDpcbiAgICAgICAgcmV0dXJuICdGYWlsZWQgdG8gdXBkYXRlIGRhc2hib2FyZCBpdGVtIGxheW91dHMuJztcbiAgICB9XG4gIH1cbn1cblxuY2xhc3MgRGVsZXRlRGFzaGJvYXJkSXRlbUVycm9ySGFuZGxlciBleHRlbmRzIEVycm9ySGFuZGxlciB7XG4gIHB1YmxpYyBnZXRFcnJvck1lc3NhZ2UoZXJyb3I6IEdyYXBoUUxFcnJvcikge1xuICAgIHN3aXRjaCAoZXJyb3IuZXh0ZW5zaW9ucz8uY29kZSkge1xuICAgICAgZGVmYXVsdDpcbiAgICAgICAgcmV0dXJuICdGYWlsZWQgdG8gZGVsZXRlIGRhc2hib2FyZCBpdGVtLic7XG4gICAgfVxuICB9XG59XG5cbmNsYXNzIFNldERhc2hib2FyZFNjaGVkdWxlRXJyb3JIYW5kbGVyIGV4dGVuZHMgRXJyb3JIYW5kbGVyIHtcbiAgcHVibGljIGdldEVycm9yTWVzc2FnZShlcnJvcjogR3JhcGhRTEVycm9yKSB7XG4gICAgc3dpdGNoIChlcnJvci5leHRlbnNpb25zPy5jb2RlKSB7XG4gICAgICBkZWZhdWx0OlxuICAgICAgICByZXR1cm4gJ0ZhaWxlZCB0byBzZXQgZGFzaGJvYXJkIHNjaGVkdWxlLic7XG4gICAgfVxuICB9XG59XG5cbmNsYXNzIENyZWF0ZVNxbFBhaXJFcnJvckhhbmRsZXIgZXh0ZW5kcyBFcnJvckhhbmRsZXIge1xuICBwdWJsaWMgZ2V0RXJyb3JNZXNzYWdlKGVycm9yOiBHcmFwaFFMRXJyb3IpIHtcbiAgICBzd2l0Y2ggKGVycm9yLmV4dGVuc2lvbnM/LmNvZGUpIHtcbiAgICAgIGRlZmF1bHQ6XG4gICAgICAgIHJldHVybiAnRmFpbGVkIHRvIGNyZWF0ZSBxdWVzdGlvbi1zcWwgcGFpci4nO1xuICAgIH1cbiAgfVxufVxuXG5jbGFzcyBVcGRhdGVTcWxQYWlyRXJyb3JIYW5kbGVyIGV4dGVuZHMgRXJyb3JIYW5kbGVyIHtcbiAgcHVibGljIGdldEVycm9yTWVzc2FnZShlcnJvcjogR3JhcGhRTEVycm9yKSB7XG4gICAgc3dpdGNoIChlcnJvci5leHRlbnNpb25zPy5jb2RlKSB7XG4gICAgICBkZWZhdWx0OlxuICAgICAgICByZXR1cm4gJ0ZhaWxlZCB0byB1cGRhdGUgcXVlc3Rpb24tc3FsIHBhaXIuJztcbiAgICB9XG4gIH1cbn1cblxuY2xhc3MgRGVsZXRlU3FsUGFpckVycm9ySGFuZGxlciBleHRlbmRzIEVycm9ySGFuZGxlciB7XG4gIHB1YmxpYyBnZXRFcnJvck1lc3NhZ2UoZXJyb3I6IEdyYXBoUUxFcnJvcikge1xuICAgIHN3aXRjaCAoZXJyb3IuZXh0ZW5zaW9ucz8uY29kZSkge1xuICAgICAgZGVmYXVsdDpcbiAgICAgICAgcmV0dXJuICdGYWlsZWQgdG8gZGVsZXRlIHF1ZXN0aW9uLXNxbCBwYWlyLic7XG4gICAgfVxuICB9XG59XG5cbmNsYXNzIENyZWF0ZUluc3RydWN0aW9uRXJyb3JIYW5kbGVyIGV4dGVuZHMgRXJyb3JIYW5kbGVyIHtcbiAgcHVibGljIGdldEVycm9yTWVzc2FnZShlcnJvcjogR3JhcGhRTEVycm9yKSB7XG4gICAgc3dpdGNoIChlcnJvci5leHRlbnNpb25zPy5jb2RlKSB7XG4gICAgICBkZWZhdWx0OlxuICAgICAgICByZXR1cm4gJ0ZhaWxlZCB0byBjcmVhdGUgaW5zdHJ1Y3Rpb24uJztcbiAgICB9XG4gIH1cbn1cblxuY2xhc3MgVXBkYXRlSW5zdHJ1Y3Rpb25FcnJvckhhbmRsZXIgZXh0ZW5kcyBFcnJvckhhbmRsZXIge1xuICBwdWJsaWMgZ2V0RXJyb3JNZXNzYWdlKGVycm9yOiBHcmFwaFFMRXJyb3IpIHtcbiAgICBzd2l0Y2ggKGVycm9yLmV4dGVuc2lvbnM/LmNvZGUpIHtcbiAgICAgIGRlZmF1bHQ6XG4gICAgICAgIHJldHVybiAnRmFpbGVkIHRvIHVwZGF0ZSBpbnN0cnVjdGlvbi4nO1xuICAgIH1cbiAgfVxufVxuXG5jbGFzcyBEZWxldGVJbnN0cnVjdGlvbkVycm9ySGFuZGxlciBleHRlbmRzIEVycm9ySGFuZGxlciB7XG4gIHB1YmxpYyBnZXRFcnJvck1lc3NhZ2UoZXJyb3I6IEdyYXBoUUxFcnJvcikge1xuICAgIHN3aXRjaCAoZXJyb3IuZXh0ZW5zaW9ucz8uY29kZSkge1xuICAgICAgZGVmYXVsdDpcbiAgICAgICAgcmV0dXJuICdGYWlsZWQgdG8gZGVsZXRlIGluc3RydWN0aW9uLic7XG4gICAgfVxuICB9XG59XG5cbmVycm9ySGFuZGxlcnMuc2V0KCdTYXZlVGFibGVzJywgbmV3IFNhdmVUYWJsZXNFcnJvckhhbmRsZXIoKSk7XG5lcnJvckhhbmRsZXJzLnNldCgnU2F2ZVJlbGF0aW9ucycsIG5ldyBTYXZlUmVsYXRpb25zRXJyb3JIYW5kbGVyKCkpO1xuZXJyb3JIYW5kbGVycy5zZXQoJ0NyZWF0ZUFza2luZ1Rhc2snLCBuZXcgQ3JlYXRlQXNraW5nVGFza0Vycm9ySGFuZGxlcigpKTtcbmVycm9ySGFuZGxlcnMuc2V0KCdDcmVhdGVUaHJlYWQnLCBuZXcgQ3JlYXRlVGhyZWFkRXJyb3JIYW5kbGVyKCkpO1xuZXJyb3JIYW5kbGVycy5zZXQoJ1VwZGF0ZVRocmVhZCcsIG5ldyBVcGRhdGVUaHJlYWRFcnJvckhhbmRsZXIoKSk7XG5lcnJvckhhbmRsZXJzLnNldCgnRGVsZXRlVGhyZWFkJywgbmV3IERlbGV0ZVRocmVhZEVycm9ySGFuZGxlcigpKTtcbmVycm9ySGFuZGxlcnMuc2V0KFxuICAnQ3JlYXRlVGhyZWFkUmVzcG9uc2UnLFxuICBuZXcgQ3JlYXRlVGhyZWFkUmVzcG9uc2VFcnJvckhhbmRsZXIoKSxcbik7XG5lcnJvckhhbmRsZXJzLnNldChcbiAgJ1VwZGF0ZVRocmVhZFJlc3BvbnNlJyxcbiAgbmV3IFVwZGF0ZVRocmVhZFJlc3BvbnNlRXJyb3JIYW5kbGVyKCksXG4pO1xuZXJyb3JIYW5kbGVycy5zZXQoXG4gICdHZW5lcmF0ZVRocmVhZFJlc3BvbnNlQW5zd2VyJyxcbiAgbmV3IEdlbmVyYXRlVGhyZWFkUmVzcG9uc2VBbnN3ZXJFcnJvckhhbmRsZXIoKSxcbik7XG5lcnJvckhhbmRsZXJzLnNldChcbiAgJ0FkanVzdFRocmVhZFJlc3BvbnNlJyxcbiAgbmV3IEFkanVzdFRocmVhZFJlc3BvbnNlRXJyb3JIYW5kbGVyKCksXG4pO1xuXG5lcnJvckhhbmRsZXJzLnNldCgnQ3JlYXRlVmlldycsIG5ldyBDcmVhdGVWaWV3RXJyb3JIYW5kbGVyKCkpO1xuZXJyb3JIYW5kbGVycy5zZXQoJ1VwZGF0ZURhdGFTb3VyY2UnLCBuZXcgVXBkYXRlRGF0YVNvdXJjZUVycm9ySGFuZGxlcigpKTtcbmVycm9ySGFuZGxlcnMuc2V0KCdDcmVhdGVNb2RlbCcsIG5ldyBDcmVhdGVNb2RlbEVycm9ySGFuZGxlcigpKTtcbmVycm9ySGFuZGxlcnMuc2V0KCdVcGRhdGVNb2RlbCcsIG5ldyBVcGRhdGVNb2RlbEVycm9ySGFuZGxlcigpKTtcbmVycm9ySGFuZGxlcnMuc2V0KCdEZWxldGVNb2RlbCcsIG5ldyBEZWxldGVNb2RlbEVycm9ySGFuZGxlcigpKTtcbmVycm9ySGFuZGxlcnMuc2V0KCdVcGRhdGVNb2RlbE1ldGFkYXRhJywgbmV3IFVwZGF0ZU1vZGVsTWV0YWRhdGFFcnJvckhhbmRsZXIoKSk7XG5lcnJvckhhbmRsZXJzLnNldCgnVXBkYXRlVmlld01ldGFkYXRhJywgbmV3IFVwZGF0ZVZpZXdNZXRhZGF0YUVycm9ySGFuZGxlcigpKTtcbmVycm9ySGFuZGxlcnMuc2V0KFxuICAnQ3JlYXRlQ2FsY3VsYXRlZEZpZWxkJyxcbiAgbmV3IENyZWF0ZUNhbGN1bGF0ZWRGaWVsZEVycm9ySGFuZGxlcigpLFxuKTtcbmVycm9ySGFuZGxlcnMuc2V0KFxuICAnVXBkYXRlQ2FsY3VsYXRlZEZpZWxkJyxcbiAgbmV3IFVwZGF0ZUNhbGN1bGF0ZWRGaWVsZEVycm9ySGFuZGxlcigpLFxuKTtcbmVycm9ySGFuZGxlcnMuc2V0KFxuICAnRGVsZXRlQ2FsY3VsYXRlZEZpZWxkJyxcbiAgbmV3IERlbGV0ZUNhbGN1bGF0ZWRGaWVsZEVycm9ySGFuZGxlcigpLFxuKTtcblxuLy8gUmVsYXRpb25zaGlwXG5lcnJvckhhbmRsZXJzLnNldCgnQ3JlYXRlUmVsYXRpb25zaGlwJywgbmV3IENyZWF0ZVJlbGF0aW9uc2hpcEVycm9ySGFuZGxlcigpKTtcbmVycm9ySGFuZGxlcnMuc2V0KCdVcGRhdGVSZWxhdGlvbnNoaXAnLCBuZXcgVXBkYXRlUmVsYXRpb25zaGlwRXJyb3JIYW5kbGVyKCkpO1xuZXJyb3JIYW5kbGVycy5zZXQoJ0RlbGV0ZVJlbGF0aW9uc2hpcCcsIG5ldyBEZWxldGVSZWxhdGlvbnNoaXBFcnJvckhhbmRsZXIoKSk7XG5cbi8vIFNjaGVtYSBjaGFuZ2VcbmVycm9ySGFuZGxlcnMuc2V0KFxuICAnVHJpZ2dlckRhdGFTb3VyY2VEZXRlY3Rpb24nLFxuICBuZXcgVHJpZ2dlckRhdGFTb3VyY2VEZXRlY3Rpb25FcnJvckhhbmRsZXIoKSxcbik7XG5lcnJvckhhbmRsZXJzLnNldCgnUmVzb2x2ZVNjaGVtYUNoYW5nZScsIG5ldyBSZXNvbHZlU2NoZW1hQ2hhbmdlRXJyb3JIYW5kbGVyKCkpO1xuXG4vLyBEYXNoYm9hcmRcbmVycm9ySGFuZGxlcnMuc2V0KCdDcmVhdGVEYXNoYm9hcmRJdGVtJywgbmV3IENyZWF0ZURhc2hib2FyZEl0ZW1FcnJvckhhbmRsZXIoKSk7XG5lcnJvckhhbmRsZXJzLnNldCgnVXBkYXRlRGFzaGJvYXJkSXRlbScsIG5ldyBVcGRhdGVEYXNoYm9hcmRJdGVtRXJyb3JIYW5kbGVyKCkpO1xuZXJyb3JIYW5kbGVycy5zZXQoXG4gICdVcGRhdGVEYXNoYm9hcmRJdGVtTGF5b3V0cycsXG4gIG5ldyBVcGRhdGVEYXNoYm9hcmRJdGVtTGF5b3V0c0Vycm9ySGFuZGxlcigpLFxuKTtcbmVycm9ySGFuZGxlcnMuc2V0KCdEZWxldGVEYXNoYm9hcmRJdGVtJywgbmV3IERlbGV0ZURhc2hib2FyZEl0ZW1FcnJvckhhbmRsZXIoKSk7XG5lcnJvckhhbmRsZXJzLnNldChcbiAgJ1NldERhc2hib2FyZFNjaGVkdWxlJyxcbiAgbmV3IFNldERhc2hib2FyZFNjaGVkdWxlRXJyb3JIYW5kbGVyKCksXG4pO1xuXG4vLyBTUUwgUGFpclxuZXJyb3JIYW5kbGVycy5zZXQoJ0NyZWF0ZVNxbFBhaXInLCBuZXcgQ3JlYXRlU3FsUGFpckVycm9ySGFuZGxlcigpKTtcbmVycm9ySGFuZGxlcnMuc2V0KCdVcGRhdGVTcWxQYWlyJywgbmV3IFVwZGF0ZVNxbFBhaXJFcnJvckhhbmRsZXIoKSk7XG5lcnJvckhhbmRsZXJzLnNldCgnRGVsZXRlU3FsUGFpcicsIG5ldyBEZWxldGVTcWxQYWlyRXJyb3JIYW5kbGVyKCkpO1xuXG4vLyBJbnN0cnVjdGlvblxuZXJyb3JIYW5kbGVycy5zZXQoJ0NyZWF0ZUluc3RydWN0aW9uJywgbmV3IENyZWF0ZUluc3RydWN0aW9uRXJyb3JIYW5kbGVyKCkpO1xuZXJyb3JIYW5kbGVycy5zZXQoJ1VwZGF0ZUluc3RydWN0aW9uJywgbmV3IFVwZGF0ZUluc3RydWN0aW9uRXJyb3JIYW5kbGVyKCkpO1xuZXJyb3JIYW5kbGVycy5zZXQoJ0RlbGV0ZUluc3RydWN0aW9uJywgbmV3IERlbGV0ZUluc3RydWN0aW9uRXJyb3JIYW5kbGVyKCkpO1xuXG5jb25zdCBlcnJvckhhbmRsZXIgPSAoZXJyb3I6IEVycm9yUmVzcG9uc2UpID0+IHtcbiAgLy8gbmV0d29ya0Vycm9yXG4gIGlmIChlcnJvci5uZXR3b3JrRXJyb3IpIHtcbiAgICBtZXNzYWdlLmVycm9yKFxuICAgICAgJ05vIGludGVybmV0LiBQbGVhc2UgY2hlY2sgeW91ciBuZXR3b3JrIGNvbm5lY3Rpb24gYW5kIHRyeSBhZ2Fpbi4nLFxuICAgICk7XG4gIH1cblxuICBjb25zdCBvcGVyYXRpb25OYW1lID0gZXJyb3I/Lm9wZXJhdGlvbj8ub3BlcmF0aW9uTmFtZSB8fCAnJztcbiAgaWYgKGVycm9yLmdyYXBoUUxFcnJvcnMpIHtcbiAgICBmb3IgKGNvbnN0IGVyciBvZiBlcnJvci5ncmFwaFFMRXJyb3JzKSB7XG4gICAgICBlcnJvckhhbmRsZXJzLmdldChvcGVyYXRpb25OYW1lKT8uaGFuZGxlKGVycik7XG4gICAgfVxuICB9XG59O1xuXG5leHBvcnQgZGVmYXVsdCBlcnJvckhhbmRsZXI7XG5cbmV4cG9ydCBjb25zdCBwYXJzZUdyYXBoUUxFcnJvciA9IChlcnJvcjogQXBvbGxvRXJyb3IpID0+IHtcbiAgaWYgKCFlcnJvcikgcmV0dXJuIG51bGw7XG4gIGNvbnN0IGdyYXBoUUxFcnJvcnM6IEdyYXBoUUxFcnJvciA9IGVycm9yLmdyYXBoUUxFcnJvcnM/LlswXTtcbiAgY29uc3QgZXh0ZW5zaW9ucyA9IGdyYXBoUUxFcnJvcnM/LmV4dGVuc2lvbnMgfHwge307XG4gIHJldHVybiB7XG4gICAgbWVzc2FnZTogZXh0ZW5zaW9ucy5tZXNzYWdlIGFzIHN0cmluZyxcbiAgICBzaG9ydE1lc3NhZ2U6IGV4dGVuc2lvbnMuc2hvcnRNZXNzYWdlIGFzIHN0cmluZyxcbiAgICBjb2RlOiBleHRlbnNpb25zLmNvZGUgYXMgc3RyaW5nLFxuICAgIHN0YWNrdHJhY2U6IGV4dGVuc2lvbnM/LnN0YWNrdHJhY2UgYXMgQXJyYXk8c3RyaW5nPiB8IHVuZGVmaW5lZCxcbiAgfTtcbn07XG4iXSwibmFtZXMiOlsibWVzc2FnZSIsIkVSUk9SX0NPREVTIiwiSU5WQUxJRF9DQUxDVUxBVEVEX0ZJRUxEIiwiQ09OTkVDVElPTl9SRUZVU0VEIiwiTk9fQ0hBUlQiLCJyZXBsYWNlTWVzc2FnZSIsImRldGFpbE1lc3NhZ2UiLCJyZWdleCIsInRleHRXaXRob3V0VG9rZW5SZWdleCIsIm1hdGNoVGV4dCIsIm1hdGNoIiwiY29uc29sZSIsIndhcm4iLCJyZXBsYWNlIiwiRXJyb3JIYW5kbGVyIiwiaGFuZGxlIiwiZXJyb3IiLCJlcnJvck1lc3NhZ2UiLCJnZXRFcnJvck1lc3NhZ2UiLCJlcnJvckhhbmRsZXJzIiwiTWFwIiwiU2F2ZVRhYmxlc0Vycm9ySGFuZGxlciIsImV4dGVuc2lvbnMiLCJjb2RlIiwiU2F2ZVJlbGF0aW9uc0Vycm9ySGFuZGxlciIsIkNyZWF0ZUFza2luZ1Rhc2tFcnJvckhhbmRsZXIiLCJDcmVhdGVUaHJlYWRFcnJvckhhbmRsZXIiLCJVcGRhdGVUaHJlYWRFcnJvckhhbmRsZXIiLCJEZWxldGVUaHJlYWRFcnJvckhhbmRsZXIiLCJDcmVhdGVUaHJlYWRSZXNwb25zZUVycm9ySGFuZGxlciIsIlVwZGF0ZVRocmVhZFJlc3BvbnNlRXJyb3JIYW5kbGVyIiwiR2VuZXJhdGVUaHJlYWRSZXNwb25zZUFuc3dlckVycm9ySGFuZGxlciIsIkFkanVzdFRocmVhZFJlc3BvbnNlRXJyb3JIYW5kbGVyIiwiQ3JlYXRlVmlld0Vycm9ySGFuZGxlciIsIlVwZGF0ZURhdGFTb3VyY2VFcnJvckhhbmRsZXIiLCJDcmVhdGVNb2RlbEVycm9ySGFuZGxlciIsIlVwZGF0ZU1vZGVsRXJyb3JIYW5kbGVyIiwiRGVsZXRlTW9kZWxFcnJvckhhbmRsZXIiLCJVcGRhdGVNb2RlbE1ldGFkYXRhRXJyb3JIYW5kbGVyIiwiQ3JlYXRlQ2FsY3VsYXRlZEZpZWxkRXJyb3JIYW5kbGVyIiwiVXBkYXRlQ2FsY3VsYXRlZEZpZWxkRXJyb3JIYW5kbGVyIiwiRGVsZXRlQ2FsY3VsYXRlZEZpZWxkRXJyb3JIYW5kbGVyIiwiQ3JlYXRlUmVsYXRpb25zaGlwRXJyb3JIYW5kbGVyIiwiVXBkYXRlUmVsYXRpb25zaGlwRXJyb3JIYW5kbGVyIiwiRGVsZXRlUmVsYXRpb25zaGlwRXJyb3JIYW5kbGVyIiwiVXBkYXRlVmlld01ldGFkYXRhRXJyb3JIYW5kbGVyIiwiVHJpZ2dlckRhdGFTb3VyY2VEZXRlY3Rpb25FcnJvckhhbmRsZXIiLCJSZXNvbHZlU2NoZW1hQ2hhbmdlRXJyb3JIYW5kbGVyIiwiQ3JlYXRlRGFzaGJvYXJkSXRlbUVycm9ySGFuZGxlciIsIlVwZGF0ZURhc2hib2FyZEl0ZW1FcnJvckhhbmRsZXIiLCJVcGRhdGVEYXNoYm9hcmRJdGVtTGF5b3V0c0Vycm9ySGFuZGxlciIsIkRlbGV0ZURhc2hib2FyZEl0ZW1FcnJvckhhbmRsZXIiLCJTZXREYXNoYm9hcmRTY2hlZHVsZUVycm9ySGFuZGxlciIsIkNyZWF0ZVNxbFBhaXJFcnJvckhhbmRsZXIiLCJVcGRhdGVTcWxQYWlyRXJyb3JIYW5kbGVyIiwiRGVsZXRlU3FsUGFpckVycm9ySGFuZGxlciIsIkNyZWF0ZUluc3RydWN0aW9uRXJyb3JIYW5kbGVyIiwiVXBkYXRlSW5zdHJ1Y3Rpb25FcnJvckhhbmRsZXIiLCJEZWxldGVJbnN0cnVjdGlvbkVycm9ySGFuZGxlciIsInNldCIsImVycm9ySGFuZGxlciIsIm5ldHdvcmtFcnJvciIsIm9wZXJhdGlvbk5hbWUiLCJvcGVyYXRpb24iLCJncmFwaFFMRXJyb3JzIiwiZXJyIiwiZ2V0IiwicGFyc2VHcmFwaFFMRXJyb3IiLCJzaG9ydE1lc3NhZ2UiLCJzdGFja3RyYWNlIl0sInNvdXJjZVJvb3QiOiIifQ==\n//# sourceURL=webpack-internal:///./src/utils/errorHandler.tsx\n");

/***/ }),

/***/ "./src/utils/telemetry.ts":
/*!********************************!*\
  !*** ./src/utils/telemetry.ts ***!
  \********************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   trackUserTelemetry: () => (/* binding */ trackUserTelemetry)\n/* harmony export */ });\n/* harmony import */ var posthog_js__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! posthog-js */ \"posthog-js\");\n/* harmony import */ var posthog_js__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(posthog_js__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var _utils_env__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @/utils/env */ \"./src/utils/env.ts\");\n\n\nconst setupPostHog = (userConfig)=>{\n    // Check that PostHog is client-side (used to handle Next.js SSR)\n    if (false) {}\n};\nconst trackUserTelemetry = (router, config)=>{\n    const handlePostHogPageView = ()=>{\n        posthog_js__WEBPACK_IMPORTED_MODULE_0___default().capture(\"$pageview\");\n    };\n    // Track PostHog\n    if (config.isTelemetryEnabled) {\n        setupPostHog(config);\n        router.events.on(\"routeChangeComplete\", handlePostHogPageView);\n    }\n    return ()=>{\n        router.events.off(\"routeChangeComplete\", handlePostHogPageView);\n    };\n};\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiLi9zcmMvdXRpbHMvdGVsZW1ldHJ5LnRzIiwibWFwcGluZ3MiOiI7Ozs7Ozs7QUFBaUM7QUFFYTtBQUU5QyxNQUFNRSxlQUFlLENBQUNDO0lBQ3BCLGlFQUFpRTtJQUNqRSxJQUFJLEtBQWtCLEVBQWEsRUFxQmxDO0FBQ0g7QUFFTyxNQUFNb0IscUJBQXFCLENBQUNDLFFBQW9CQztJQUNyRCxNQUFNQyx3QkFBd0I7UUFDNUIxQix5REFBZSxDQUFDO0lBQ2xCO0lBRUEsZ0JBQWdCO0lBQ2hCLElBQUl5QixPQUFPRyxrQkFBa0IsRUFBRTtRQUM3QjFCLGFBQWF1QjtRQUNiRCxPQUFPSyxNQUFNLENBQUNDLEVBQUUsQ0FBQyx1QkFBdUJKO0lBQzFDO0lBRUEsT0FBTztRQUNMRixPQUFPSyxNQUFNLENBQUNFLEdBQUcsQ0FBQyx1QkFBdUJMO0lBQzNDO0FBQ0YsRUFBRSIsInNvdXJjZXMiOlsid2VicGFjazovL3dyZW4tdWkvLi9zcmMvdXRpbHMvdGVsZW1ldHJ5LnRzP2M1ZDUiXSwic291cmNlc0NvbnRlbnQiOlsiaW1wb3J0IHBvc3Rob2cgZnJvbSAncG9zdGhvZy1qcyc7XG5pbXBvcnQgeyBOZXh0Um91dGVyIH0gZnJvbSAnbmV4dC9yb3V0ZXInO1xuaW1wb3J0IGVudiwgeyBVc2VyQ29uZmlnIH0gZnJvbSAnQC91dGlscy9lbnYnO1xuXG5jb25zdCBzZXR1cFBvc3RIb2cgPSAodXNlckNvbmZpZykgPT4ge1xuICAvLyBDaGVjayB0aGF0IFBvc3RIb2cgaXMgY2xpZW50LXNpZGUgKHVzZWQgdG8gaGFuZGxlIE5leHQuanMgU1NSKVxuICBpZiAodHlwZW9mIHdpbmRvdyAhPT0gJ3VuZGVmaW5lZCcpIHtcbiAgICBwb3N0aG9nLmluaXQodXNlckNvbmZpZy50ZWxlbWV0cnlLZXksIHtcbiAgICAgIGFwaV9ob3N0OiB1c2VyQ29uZmlnLnRlbGVtZXRyeUhvc3QsXG4gICAgICBhdXRvY2FwdHVyZToge1xuICAgICAgICBkb21fZXZlbnRfYWxsb3dsaXN0OiBbJ2NsaWNrJ10sXG4gICAgICAgIGNzc19zZWxlY3Rvcl9hbGxvd2xpc3Q6IFsnW2RhdGEtcGgtY2FwdHVyZT1cInRydWVcIl0nXSxcbiAgICAgIH0sXG4gICAgICBzZXNzaW9uX3JlY29yZGluZzoge1xuICAgICAgICBtYXNrQWxsSW5wdXRzOiBmYWxzZSxcbiAgICAgICAgbWFza0lucHV0T3B0aW9uczoge1xuICAgICAgICAgIHBhc3N3b3JkOiB0cnVlLFxuICAgICAgICB9LFxuICAgICAgfSxcbiAgICAgIGRpc2FibGVfc2Vzc2lvbl9yZWNvcmRpbmc6IGVudi5pc0RldmVsb3BtZW50LFxuICAgICAgZGVidWc6IGZhbHNlLFxuICAgICAgbG9hZGVkOiAoKSA9PiB7XG4gICAgICAgIGNvbnNvbGUubG9nKCdQb3N0SG9nIGluaXRpYWxpemVkLicpO1xuICAgICAgfSxcbiAgICB9KTtcbiAgICAvLyBzZXQgdXAgZGlzdGluY3QgaWQgdG8gcG9zdGhvZ1xuICAgIGlmICh1c2VyQ29uZmlnLnVzZXJVVUlEKSBwb3N0aG9nLmlkZW50aWZ5KHVzZXJDb25maWcudXNlclVVSUQpO1xuICB9XG59O1xuXG5leHBvcnQgY29uc3QgdHJhY2tVc2VyVGVsZW1ldHJ5ID0gKHJvdXRlcjogTmV4dFJvdXRlciwgY29uZmlnOiBVc2VyQ29uZmlnKSA9PiB7XG4gIGNvbnN0IGhhbmRsZVBvc3RIb2dQYWdlVmlldyA9ICgpID0+IHtcbiAgICBwb3N0aG9nLmNhcHR1cmUoJyRwYWdldmlldycpO1xuICB9O1xuXG4gIC8vIFRyYWNrIFBvc3RIb2dcbiAgaWYgKGNvbmZpZy5pc1RlbGVtZXRyeUVuYWJsZWQpIHtcbiAgICBzZXR1cFBvc3RIb2coY29uZmlnKTtcbiAgICByb3V0ZXIuZXZlbnRzLm9uKCdyb3V0ZUNoYW5nZUNvbXBsZXRlJywgaGFuZGxlUG9zdEhvZ1BhZ2VWaWV3KTtcbiAgfVxuXG4gIHJldHVybiAoKSA9PiB7XG4gICAgcm91dGVyLmV2ZW50cy5vZmYoJ3JvdXRlQ2hhbmdlQ29tcGxldGUnLCBoYW5kbGVQb3N0SG9nUGFnZVZpZXcpO1xuICB9O1xufTtcbiJdLCJuYW1lcyI6WyJwb3N0aG9nIiwiZW52Iiwic2V0dXBQb3N0SG9nIiwidXNlckNvbmZpZyIsImluaXQiLCJ0ZWxlbWV0cnlLZXkiLCJhcGlfaG9zdCIsInRlbGVtZXRyeUhvc3QiLCJhdXRvY2FwdHVyZSIsImRvbV9ldmVudF9hbGxvd2xpc3QiLCJjc3Nfc2VsZWN0b3JfYWxsb3dsaXN0Iiwic2Vzc2lvbl9yZWNvcmRpbmciLCJtYXNrQWxsSW5wdXRzIiwibWFza0lucHV0T3B0aW9ucyIsInBhc3N3b3JkIiwiZGlzYWJsZV9zZXNzaW9uX3JlY29yZGluZyIsImlzRGV2ZWxvcG1lbnQiLCJkZWJ1ZyIsImxvYWRlZCIsImNvbnNvbGUiLCJsb2ciLCJ1c2VyVVVJRCIsImlkZW50aWZ5IiwidHJhY2tVc2VyVGVsZW1ldHJ5Iiwicm91dGVyIiwiY29uZmlnIiwiaGFuZGxlUG9zdEhvZ1BhZ2VWaWV3IiwiY2FwdHVyZSIsImlzVGVsZW1ldHJ5RW5hYmxlZCIsImV2ZW50cyIsIm9uIiwib2ZmIl0sInNvdXJjZVJvb3QiOiIifQ==\n//# sourceURL=webpack-internal:///./src/utils/telemetry.ts\n");

/***/ }),

/***/ "./src/styles/index.less":
/*!*******************************!*\
  !*** ./src/styles/index.less ***!
  \*******************************/
/***/ (() => {



/***/ }),

/***/ "@ant-design/colors":
/*!*************************************!*\
  !*** external "@ant-design/colors" ***!
  \*************************************/
/***/ ((module) => {

"use strict";
module.exports = require("@ant-design/colors");

/***/ }),

/***/ "@ant-design/icons-svg/lib/asn/CheckCircleFilled":
/*!******************************************************************!*\
  !*** external "@ant-design/icons-svg/lib/asn/CheckCircleFilled" ***!
  \******************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("@ant-design/icons-svg/lib/asn/CheckCircleFilled");

/***/ }),

/***/ "@ant-design/icons-svg/lib/asn/CheckCircleOutlined":
/*!********************************************************************!*\
  !*** external "@ant-design/icons-svg/lib/asn/CheckCircleOutlined" ***!
  \********************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("@ant-design/icons-svg/lib/asn/CheckCircleOutlined");

/***/ }),

/***/ "@ant-design/icons-svg/lib/asn/CloseCircleFilled":
/*!******************************************************************!*\
  !*** external "@ant-design/icons-svg/lib/asn/CloseCircleFilled" ***!
  \******************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("@ant-design/icons-svg/lib/asn/CloseCircleFilled");

/***/ }),

/***/ "@ant-design/icons-svg/lib/asn/CloseCircleOutlined":
/*!********************************************************************!*\
  !*** external "@ant-design/icons-svg/lib/asn/CloseCircleOutlined" ***!
  \********************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("@ant-design/icons-svg/lib/asn/CloseCircleOutlined");

/***/ }),

/***/ "@ant-design/icons-svg/lib/asn/CloseOutlined":
/*!**************************************************************!*\
  !*** external "@ant-design/icons-svg/lib/asn/CloseOutlined" ***!
  \**************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("@ant-design/icons-svg/lib/asn/CloseOutlined");

/***/ }),

/***/ "@ant-design/icons-svg/lib/asn/ExclamationCircleFilled":
/*!************************************************************************!*\
  !*** external "@ant-design/icons-svg/lib/asn/ExclamationCircleFilled" ***!
  \************************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("@ant-design/icons-svg/lib/asn/ExclamationCircleFilled");

/***/ }),

/***/ "@ant-design/icons-svg/lib/asn/ExclamationCircleOutlined":
/*!**************************************************************************!*\
  !*** external "@ant-design/icons-svg/lib/asn/ExclamationCircleOutlined" ***!
  \**************************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("@ant-design/icons-svg/lib/asn/ExclamationCircleOutlined");

/***/ }),

/***/ "@ant-design/icons-svg/lib/asn/InfoCircleFilled":
/*!*****************************************************************!*\
  !*** external "@ant-design/icons-svg/lib/asn/InfoCircleFilled" ***!
  \*****************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("@ant-design/icons-svg/lib/asn/InfoCircleFilled");

/***/ }),

/***/ "@ant-design/icons-svg/lib/asn/InfoCircleOutlined":
/*!*******************************************************************!*\
  !*** external "@ant-design/icons-svg/lib/asn/InfoCircleOutlined" ***!
  \*******************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("@ant-design/icons-svg/lib/asn/InfoCircleOutlined");

/***/ }),

/***/ "@ant-design/icons-svg/lib/asn/LoadingOutlined":
/*!****************************************************************!*\
  !*** external "@ant-design/icons-svg/lib/asn/LoadingOutlined" ***!
  \****************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("@ant-design/icons-svg/lib/asn/LoadingOutlined");

/***/ }),

/***/ "@apollo/client":
/*!*********************************!*\
  !*** external "@apollo/client" ***!
  \*********************************/
/***/ ((module) => {

"use strict";
module.exports = require("@apollo/client");

/***/ }),

/***/ "@apollo/client/link/error":
/*!********************************************!*\
  !*** external "@apollo/client/link/error" ***!
  \********************************************/
/***/ ((module) => {

"use strict";
module.exports = require("@apollo/client/link/error");

/***/ }),

/***/ "@ctrl/tinycolor":
/*!**********************************!*\
  !*** external "@ctrl/tinycolor" ***!
  \**********************************/
/***/ ((module) => {

"use strict";
module.exports = require("@ctrl/tinycolor");

/***/ }),

/***/ "classnames":
/*!*****************************!*\
  !*** external "classnames" ***!
  \*****************************/
/***/ ((module) => {

"use strict";
module.exports = require("classnames");

/***/ }),

/***/ "lodash/camelCase":
/*!***********************************!*\
  !*** external "lodash/camelCase" ***!
  \***********************************/
/***/ ((module) => {

"use strict";
module.exports = require("lodash/camelCase");

/***/ }),

/***/ "lodash/debounce":
/*!**********************************!*\
  !*** external "lodash/debounce" ***!
  \**********************************/
/***/ ((module) => {

"use strict";
module.exports = require("lodash/debounce");

/***/ }),

/***/ "memoize-one":
/*!******************************!*\
  !*** external "memoize-one" ***!
  \******************************/
/***/ ((module) => {

"use strict";
module.exports = require("memoize-one");

/***/ }),

/***/ "next/dist/compiled/next-server/pages.runtime.dev.js":
/*!**********************************************************************!*\
  !*** external "next/dist/compiled/next-server/pages.runtime.dev.js" ***!
  \**********************************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("next/dist/compiled/next-server/pages.runtime.dev.js");

/***/ }),

/***/ "next/head":
/*!****************************!*\
  !*** external "next/head" ***!
  \****************************/
/***/ ((module) => {

"use strict";
module.exports = require("next/head");

/***/ }),

/***/ "posthog-js":
/*!*****************************!*\
  !*** external "posthog-js" ***!
  \*****************************/
/***/ ((module) => {

"use strict";
module.exports = require("posthog-js");

/***/ }),

/***/ "posthog-js/react":
/*!***********************************!*\
  !*** external "posthog-js/react" ***!
  \***********************************/
/***/ ((module) => {

"use strict";
module.exports = require("posthog-js/react");

/***/ }),

/***/ "rc-field-form":
/*!********************************!*\
  !*** external "rc-field-form" ***!
  \********************************/
/***/ ((module) => {

"use strict";
module.exports = require("rc-field-form");

/***/ }),

/***/ "rc-notification":
/*!**********************************!*\
  !*** external "rc-notification" ***!
  \**********************************/
/***/ ((module) => {

"use strict";
module.exports = require("rc-notification");

/***/ }),

/***/ "rc-notification/lib/useNotification":
/*!******************************************************!*\
  !*** external "rc-notification/lib/useNotification" ***!
  \******************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("rc-notification/lib/useNotification");

/***/ }),

/***/ "rc-pagination/lib/locale/en_US":
/*!*************************************************!*\
  !*** external "rc-pagination/lib/locale/en_US" ***!
  \*************************************************/
/***/ ((module) => {

"use strict";
module.exports = require("rc-pagination/lib/locale/en_US");

/***/ }),

/***/ "rc-picker/lib/locale/en_US":
/*!*********************************************!*\
  !*** external "rc-picker/lib/locale/en_US" ***!
  \*********************************************/
/***/ ((module) => {

"use strict";
module.exports = require("rc-picker/lib/locale/en_US");

/***/ }),

/***/ "rc-util/lib/Dom/canUseDom":
/*!********************************************!*\
  !*** external "rc-util/lib/Dom/canUseDom" ***!
  \********************************************/
/***/ ((module) => {

"use strict";
module.exports = require("rc-util/lib/Dom/canUseDom");

/***/ }),

/***/ "rc-util/lib/Dom/dynamicCSS":
/*!*********************************************!*\
  !*** external "rc-util/lib/Dom/dynamicCSS" ***!
  \*********************************************/
/***/ ((module) => {

"use strict";
module.exports = require("rc-util/lib/Dom/dynamicCSS");

/***/ }),

/***/ "rc-util/lib/hooks/useMemo":
/*!********************************************!*\
  !*** external "rc-util/lib/hooks/useMemo" ***!
  \********************************************/
/***/ ((module) => {

"use strict";
module.exports = require("rc-util/lib/hooks/useMemo");

/***/ }),

/***/ "rc-util/lib/omit":
/*!***********************************!*\
  !*** external "rc-util/lib/omit" ***!
  \***********************************/
/***/ ((module) => {

"use strict";
module.exports = require("rc-util/lib/omit");

/***/ }),

/***/ "rc-util/lib/warning":
/*!**************************************!*\
  !*** external "rc-util/lib/warning" ***!
  \**************************************/
/***/ ((module) => {

"use strict";
module.exports = require("rc-util/lib/warning");

/***/ }),

/***/ "react":
/*!************************!*\
  !*** external "react" ***!
  \************************/
/***/ ((module) => {

"use strict";
module.exports = require("react");

/***/ }),

/***/ "react-dom":
/*!****************************!*\
  !*** external "react-dom" ***!
  \****************************/
/***/ ((module) => {

"use strict";
module.exports = require("react-dom");

/***/ }),

/***/ "react/jsx-dev-runtime":
/*!****************************************!*\
  !*** external "react/jsx-dev-runtime" ***!
  \****************************************/
/***/ ((module) => {

"use strict";
module.exports = require("react/jsx-dev-runtime");

/***/ }),

/***/ "react/jsx-runtime":
/*!************************************!*\
  !*** external "react/jsx-runtime" ***!
  \************************************/
/***/ ((module) => {

"use strict";
module.exports = require("react/jsx-runtime");

/***/ }),

/***/ "styled-components":
/*!************************************!*\
  !*** external "styled-components" ***!
  \************************************/
/***/ ((module) => {

"use strict";
module.exports = require("styled-components");

/***/ }),

/***/ "fs":
/*!*********************!*\
  !*** external "fs" ***!
  \*********************/
/***/ ((module) => {

"use strict";
module.exports = require("fs");

/***/ }),

/***/ "stream":
/*!*************************!*\
  !*** external "stream" ***!
  \*************************/
/***/ ((module) => {

"use strict";
module.exports = require("stream");

/***/ }),

/***/ "zlib":
/*!***********************!*\
  !*** external "zlib" ***!
  \***********************/
/***/ ((module) => {

"use strict";
module.exports = require("zlib");

/***/ })

};
;

// load runtime
var __webpack_require__ = require("../webpack-runtime.js");
__webpack_require__.C(exports);
var __webpack_exec__ = (moduleId) => (__webpack_require__(__webpack_require__.s = moduleId))
var __webpack_exports__ = __webpack_require__.X(0, ["vendor-chunks/next","vendor-chunks/@ant-design","vendor-chunks/@swc","vendor-chunks/antd","vendor-chunks/@babel"], () => (__webpack_exec__("./src/pages/_app.tsx")));
module.exports = __webpack_exports__;

})();