import React, { useState, useEffect, useContext } from "react";
import { API_BASE_URL } from "../utils/api";
import { AuthContext } from "../contexts/AuthContext";

// Formatera JSON med kompakta objekter för {"v": value, "p": probability} struktur
const formatJsonCompact = (obj, indent = 0) => {
  const spaces = "  ".repeat(indent);
  
  if (obj === null || obj === undefined) {
    return "null";
  }
  
  if (typeof obj !== "object") {
    if (typeof obj === "string") {
      return `"${obj}"`;
    }
    return String(obj);
  }
  
  if (Array.isArray(obj)) {
    if (obj.length === 0) return "[]";
    const items = obj.map(item => `${spaces}  ${formatJsonCompact(item, indent + 1)}`).join(",\n");
    return `[\n${items}\n${spaces}]`;
  }
  
  // Checks om objektet är {"v": ..., "p": ...} struktur
  if (obj.hasOwnProperty("v") && obj.hasOwnProperty("p") && Object.keys(obj).length === 2) {
    const value = typeof obj.v === "string" ? `"${obj.v}"` : formatJsonCompact(obj.v);
    const probability = obj.p !== null && obj.p !== undefined ? obj.p : "null";
    return `{"v": ${value}, "p": ${probability}}`;
  }
  
  // Vanligt objekt - multi-line format
  const keys = Object.keys(obj);
  if (keys.length === 0) return "{}";
  
  const lines = keys.map(key => {
    const value = obj[key];
    if (value !== null && typeof value === "object" && value.hasOwnProperty("v") && value.hasOwnProperty("p") && Object.keys(value).length === 2) {
      // Kompakt format för {"v", "p"}
      const v = typeof value.v === "string" ? `"${value.v}"` : formatJsonCompact(value.v);
      const p = value.p !== null && value.p !== undefined ? value.p : "null";
      return `${spaces}  "${key}": {"v": ${v}, "p": ${p}}`;
    } else {
      return `${spaces}  "${key}": ${formatJsonCompact(value, indent + 1)}`;
    }
  }).join(",\n");
  
  return `{\n${lines}\n${spaces}}`;
};

function DocumentDetail({ document, peppolSections = "", onClose, onSave }) {
  const { user } = useContext(AuthContext);
  const isAdmin = user?.role_key === 1000 || user?.role_key === 50;
  
  // Parse XML schema once
  const [peppol_sections, setPeppolSections] = useState({});
  const [showAdvancedAnalysis, setShowAdvancedAnalysis] = useState(false);
  const [activeAnalysisTab, setActiveAnalysisTab] = useState("extraction");
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  // Parse XML on mount or when peppolSections changes
  useEffect(() => {
    if (peppolSections && typeof peppolSections === 'string') {
      try {
        console.log('[XML Parse] Starting PEPPOL XML parse...');
        console.log('[XML Parse] Received XML length:', peppolSections.length, 'bytes');
        
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(peppolSections, "application/xml");

        // Tvinga fram felmeddelandet från parsern
        const parseErrors = xmlDoc.getElementsByTagName("parsererror");
        if (parseErrors.length > 0) {
            console.error('[XML Parse] ❌ Ett fel uppstod vid parsing.');
            
            // 1. Skriv ut felmeddelandet (innehåller ofta radnummer)
            console.error('Feldetaljer:', parseErrors[0].textContent);

            // 2. Hitta den sista giltiga noden innan felet
            // Vi letar i hela dokumentet efter det sista elementet som inte är parsererror
            const allNodes = xmlDoc.getElementsByTagName('*');
            let lastValidNode = null;
            
            for (let i = 0; i < allNodes.length; i++) {
                if (allNodes[i].tagName !== 'parsererror' && !allNodes[i].closest('parsererror')) {
                    lastValidNode = allNodes[i];
                }
            }

            if (lastValidNode) {
                console.log('%c Sista lyckade noden innan krasch: ', 'background: #222; color: #bada55');
                console.log('Tagg-namn:', lastValidNode.tagName);
                console.log('Innehåll (förkortat):', lastValidNode.outerHTML.substring(0, 200) + '...');
                console.log('Mapid:', lastValidNode.getAttribute('mapid'));
            }
            return

        }



        /*
        const allElements = xmlDoc.getElementsByTagName('*');
        console.log(`[XML Parse] Totalt antal element i dokumentet: ${allElements.length}`);

        const mapidData = Array.from(allElements)
          .filter(el => el.hasAttribute('mapid'))
          .map(el => ({
            tag: el.tagName,
            mapid: el.getAttribute('mapid'),
            namespace: el.namespaceURI
          }));

        console.table(mapidData); // Skapar en snygg tabell i konsolen med alla träffar
        */
        
        // Get namespace URLs
        const cbcNS = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2";
        const cacNS = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2";
         
        // Debug: Count ALL elements with mapid BEFORE parsing
        // Use getElementsByTagName('*') to find all elements, then filter by hasAttribute
        const allElementsWithMapid = Array.from(xmlDoc.getElementsByTagName('*')).filter(el => el.hasAttribute('mapid'));
        const cbcMapidElements = allElementsWithMapid.filter(el => el.namespaceURI === cbcNS);
 
        // Step 1: Collect ALL CBC fields from entire XML tree
        const allFields = {};
        let fieldsWithMapid = 0;
        let fieldsWithoutMapid = 0;
        const fieldsWithMapidList = [];
        const contextOrder = ['Invoice.Meta', 'Supplier', 'Customer', 'Payee', 'Tax Representative', 'Delivery', 'Payment', 'Charges.Discounts', 'Tax', 'Totals', 'LineItem'];
        
        function collectAllFields(elem) {
          for (let child of elem.children) {
            const namespace = child.namespaceURI;
            const btId = child.getAttribute('BT-ID');
            const mapid = child.getAttribute('mapid');
            
            // Index by mapid (always present on CBC elements)
            if (namespace === cbcNS && mapid) {
              fieldsWithMapid++;
              fieldsWithMapidList.push({ btId, mapid });
              
              // Extract all attributes
              const advancedAttr = child.getAttribute('Advanced');
              const obligationAttr = child.getAttribute('Obligation');
              const displayName = child.getAttribute('DisplayName');
              
              const fieldInfo = {
                'mapid': mapid,
                'BT-ID': btId || 'N/A',
                'TagName': child.localName,
                'DisplayName': displayName || child.localName,
                'DisplayContext': child.getAttribute('DisplayContext') || 'Other',
                'Description': child.getAttribute('Description') || '',
                'Obligation': obligationAttr || 'optional',
                'Type': child.getAttribute('Type') || '',
                'Example': child.getAttribute('Example') || '',
                'UBL-XPath': child.getAttribute('UBL-XPath') || '',
                'Advanced': advancedAttr === 'true',
                'ConditionalDescription': child.getAttribute('ConditionalDescription') || ''
              };
              
              allFields[mapid] = fieldInfo;
            }
            
            // RECURSIVE: Always recurse into ALL child elements
            collectAllFields(child);
          }
        }
        
        // Collect all fields starting from root
        const root = xmlDoc.documentElement;
        collectAllFields(root);
        
        console.log(`[XML Parse] Total fields collected: ${Object.keys(allFields).length}`);
        
        // Step 2: Group fields by DisplayContext
        const sections = {};
        contextOrder.forEach(context => {
          sections[context] = { fields: {}, nested: {} };
        });
        
        Object.entries(allFields).forEach(([mapid, fieldInfo]) => {
          const context = fieldInfo.DisplayContext || 'Other';
          if (!sections[context]) {
            sections[context] = { fields: {}, nested: {} };
          }
          sections[context].fields[mapid] = fieldInfo;
        });
        
        // Remove empty sections
        const finalSections = Object.fromEntries(
          Object.entries(sections).filter(([_, section]) => Object.keys(section.fields).length > 0)
        );
        
        console.log('[XML Parse] Parse complete. Sections:', Object.keys(finalSections));
        console.log('[XML Parse] Fields WITH mapid:', fieldsWithMapid);
        console.log('[XML Parse] Fields WITHOUT mapid (ERROR):', fieldsWithoutMapid);
        if (fieldsWithMapid > 0) {
          console.log('[XML Parse] First 5 fields with mapid:', fieldsWithMapidList.slice(0, 5));
        }
        if (fieldsWithoutMapid > 0) {
          console.error(`[XML Parse] ❌ CRITICAL: ${fieldsWithoutMapid} fields are missing mapid attribute!`);
        }
        setPeppolSections(finalSections);
      } catch (err) {
        console.error('Error parsing PEPPOL XML:', err);
      }
    }
  }, [peppolSections]);
  
  const [invoiceData, setInvoiceData] = useState({
    document_name: "",
  });
  
  const [originalInvoiceData, setOriginalInvoiceData] = useState({});
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [showPreview, setShowPreview] = useState(true);
  const [showForm, setShowForm] = useState(true);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const [expandedSections, setExpandedSections] = useState({});
  const [showNonMandatory, setShowNonMandatory] = useState(false);
  const [lineItems, setLineItems] = useState([{ id: 0 }]); // Start with 1 empty line item
  const [expandedLineItems, setExpandedLineItems] = useState({}); // Track which line items are expanded
  const [nextLineItemId, setNextLineItemId] = useState(1); // Counter for unique IDs
  const [deletedLineNumbers, setDeletedLineNumbers] = useState([]); // Track deleted line_numbers for backend
  const [fullDocument, setFullDocument] = useState(document);
  const [loadingFullData, setLoadingFullData] = useState(false);
  const [companySettings, setCompanySettings] = useState(null);
  const [fieldProbabilities, setFieldProbabilities] = useState({});

  // Fetch full document details from backend when component mounts
  useEffect(() => {
    const loadFullDocumentDetails = async () => {
      if (document?.id) {
        setLoadingFullData(true);
        try {
          const response = await fetch(`${API_BASE_URL}/documents/${document.id}/details`, {
            method: "GET",
            credentials: "include",
            headers: {
              "Content-Type": "application/json",
            },
          });

          if (response.ok) {
            const data = await response.json();
            setFullDocument(data.document);
          } else {
            console.warn("Failed to fetch full document details");
            setFullDocument(document);
          }
        } catch (err) {
          console.error("Error loading full document details:", err);
          setFullDocument(document);
        } finally {
          setLoadingFullData(false);
        }
      }
    };

    loadFullDocumentDetails();
  }, [document?.id]);

  // Fetch company settings when document is loaded
  useEffect(() => {
    const loadCompanySettings = async () => {
      if (fullDocument?.company_id) {
        try {
          const response = await fetch(`${API_BASE_URL}/live/company-settings`, {
            method: "GET",
            credentials: "include",
            headers: {
              "Content-Type": "application/json",
            },
          });

          if (response.ok) {
            const data = await response.json();
            // API returns company_settings object
            const settings = data.company_settings || {};
            setCompanySettings(settings);
            console.log('[Form Init] Loaded company settings:', settings);
          } else {
            console.warn("Failed to fetch company settings, using defaults");
            setCompanySettings({});
          }
        } catch (err) {
          console.error("Error loading company settings:", err);
          setCompanySettings({});
        }
      }
    };

    loadCompanySettings();
  }, [fullDocument?.company_id]);

  const toggleSection = (sectionName) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionName]: !prev[sectionName]
    }));
  };

  // Line Items functions
  const addLineItem = () => {
    const newLineItem = { id: nextLineItemId };
    setLineItems([...lineItems, newLineItem]);
    // Auto-set line_number to last line_number + 1
    const lastLineNumber = lineItems.length; // Since 1-indexed, length = max+1
    const newLineItemNumber = lastLineNumber + 1;
    setInvoiceData(prev => ({
      ...prev,
      [`line_item_${nextLineItemId}.line_number`]: String(newLineItemNumber)
    }));
    setNextLineItemId(nextLineItemId + 1);
    // Auto-expand the new line item
    setExpandedLineItems(prev => ({
      ...prev,
      [newLineItem.id]: true
    }));
  };

  const removeLineItem = (id) => {
    if (lineItems.length > 1) { // Keep at least 1 line item
      // Get line_number before removing
      const lineNumber = parseInt(invoiceData[`line_item_${id}.line_number`] || '0');
      if (lineNumber > 0) {
        setDeletedLineNumbers(prev => [...prev, lineNumber]);
      }
      setLineItems(lineItems.filter(item => item.id !== id));
      setExpandedLineItems(prev => {
        const newExpanded = { ...prev };
        delete newExpanded[id];
        return newExpanded;
      });
    }
  };

  const toggleLineItem = (id) => {
    setExpandedLineItems(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const togglePreview = () => {
    if (showPreview) {
      // Trying to collapse preview
      if (!showForm) {
        // Form is already collapsed, so expand it
        setShowForm(true);
      }
      setShowPreview(false);
    } else {
      setShowPreview(true);
    }
  };

  const toggleForm = () => {
    if (showForm) {
      // Trying to collapse form
      if (!showPreview) {
        // Preview is already collapsed, so expand it
        setShowPreview(true);
      }
      setShowForm(false);
    } else {
      setShowForm(true);
    }
  };

  // Initialize invoice data and preview from document
  useEffect(() => {
    if (fullDocument) {
      const newInvoiceData = {
        document_name: fullDocument.document_name || "",
      };
      
      // If invoice_data_peppol_final exists, populate fields from it
      // Structure: { "meta": { "invoice_number": {"v": "...", "p": 0.9}, ... }, ... }
      if (fullDocument.invoice_data_peppol_final) {
        let peppol_final = fullDocument.invoice_data_peppol_final;
        
        // Parse if it's a JSON string
        if (typeof peppol_final === 'string') {
          try {
            peppol_final = JSON.parse(peppol_final);
          } catch (e) {
            console.warn('[Form Init] Failed to parse invoice_data_peppol_final:', e);
            peppol_final = {};
          }
        }
        
        console.log('[Form Init] Raw invoice_data_peppol_final:', peppol_final);
        
        // Helper: Navigate nested object using dot notation (e.g., "meta.invoice_number")
        const getNestedValue = (obj, path) => {
          const parts = path.split('.');
          let current = obj;
          
          for (let part of parts) {
            if (current && typeof current === 'object' && part in current) {
              current = current[part];
            } else {
              return null;
            }
          }
          
          return current;
        };
        
        // Helper: Extract value from {"v": value, "p": probability} format
        const extractValue = (item) => {
          if (!item) return null;
          
          // If it's {"v": ..., "p": ...} format, extract value
          if (typeof item === 'object' && item.v !== undefined) {
            return item.v;
          }
          
          // If it's simple string/number, return as-is
          if (typeof item === 'string' || typeof item === 'number') {
            return String(item);
          }
          
          return null;
        };
        
        // Flatten all nested paths - create mapid-keyed structure
        const probabilitiesMap = {};
        
        const flattenNested = (obj, prefix = '') => {
          const result = {};
          
          for (const [key, value] of Object.entries(obj || {})) {
            const mapid = prefix ? `${prefix}.${key}` : key;
            
            if (value === null || value === undefined) {
              continue;
            }
            
            // If it's {"v": ..., "p": ...} format, extract and store
            if (typeof value === 'object' && value.v !== undefined && value.p !== undefined) {
              const extracted = extractValue(value);
              if (extracted) {
                result[mapid] = extracted;
                // Store probability for this field
                probabilitiesMap[mapid] = value.p;
              }
            }
            // If it's a nested object (but NOT {"v": ..., "p": ...}), recurse
            else if (typeof value === 'object' && !Array.isArray(value)) {
              Object.assign(result, flattenNested(value, mapid));
            }
          }
          
          return result;
        };
        
        const flattenedData = flattenNested(peppol_final);
        console.log('[Form Init] Flattened data structure:', flattenedData);
        console.log('[Form Init] Total fields extracted:', Object.keys(flattenedData).length);
        console.log('[Form Init] Field probabilities:', probabilitiesMap);
        
        // Store probabilities for later use in filtering
        setFieldProbabilities(probabilitiesMap);
        
        // Populate newInvoiceData with flattened structure
        Object.assign(newInvoiceData, flattenedData);
        
        // Handle line_items - populate lineItems state and invoiceData
        if (peppol_final.line_items && Array.isArray(peppol_final.line_items)) {
          console.log('[Form Init] Found line_items array:', peppol_final.line_items);
          
          const newLineItems = [];
          let nextId = 0;
          
          peppol_final.line_items.forEach((lineItemData, index) => {
            const lineId = nextId++;
            newLineItems.push({ id: lineId });
            
            // Map each field from the line item data
            // Add line_number based on index (1-indexed)
            newInvoiceData[`line_item_${lineId}.line_number`] = String(index + 1);
            
            // Extract values for each field
            const fieldMap = {
              'quantity': 'quantity',
              'unit': 'unit',
              'line_total': 'line_total',
              'description': 'description',
              'tax_category': 'tax_category',
              'tax_rate': 'tax_rate',
              'tax_amount': 'tax_amount',
              'tax_scheme': 'tax_scheme',
              'unit_price': 'unit_price',
              'base_quantity': 'base_quantity',
              'line_number': 'line_number'
            };
            
            for (const [dataKey, fieldKey] of Object.entries(fieldMap)) {
              if (lineItemData[dataKey]) {
                const value = extractValue(lineItemData[dataKey]);
                if (value) {
                  newInvoiceData[`line_item_${lineId}.${fieldKey}`] = value;
                }
              }
            }
          });
          
          setLineItems(newLineItems);
          setNextLineItemId(nextId);
          console.log('[Form Init] Populated line items. New lineItems state:', newLineItems);
        }
        
        console.log('[Form Init] Final newInvoiceData:', newInvoiceData);
      }
      
      setInvoiceData(newInvoiceData);
      // Store original data for change tracking
      setOriginalInvoiceData(JSON.parse(JSON.stringify(newInvoiceData)));

      // Set preview URL directly - no need to fetch and convert
      // Browser will fetch it automatically with credentials
      setPreviewUrl(`${API_BASE_URL}/documents/${fullDocument.id}/preview`);
      setPreviewLoading(false);
    }
  }, [fullDocument]);

  const handleFieldChange = (field, value) => {
    setInvoiceData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSave = async () => {
    setIsLoading(true);
    setError(null);
    setSuccess(false);

    try {
      // Create delta - only include fields that have been changed
      const deltaFlat = {};
      Object.entries(invoiceData).forEach(([key, value]) => {
        const originalValue = originalInvoiceData[key];
        // Check if field value differs from original
        if (value !== originalValue) {
          deltaFlat[key] = value;
        }
      });
      
      console.log("[Save] Delta (flat mapids):", deltaFlat);
      
      // Ensure all line_numbers are included in delta (needed for deletion logic)
      // Even if line_number wasn't changed, we need it for backend to identify which lines to delete
      lineItems.forEach(lineItem => {
        const lineNumber = invoiceData[`line_item_${lineItem.id}.line_number`];
        if (lineNumber && !deltaFlat[`line_item_${lineItem.id}.line_number`]) {
          deltaFlat[`line_item_${lineItem.id}.line_number`] = lineNumber;
        }
      });
      
      // Convert flat delta to structured format matching invoice_template.json
      // Extract: section_name.field_name -> section_name: { field_name: value }
      const userCorrected = {};
      Object.entries(deltaFlat).forEach(([mapid, value]) => {
        // Skip special fields like document_name
        if (mapid === 'document_name') return;
        
        // Parse mapid format: "section.field" or "line_item_0.field"
        const parts = mapid.split('.');
        if (parts.length >= 2) {
          const firstPart = parts[0];
          const fieldName = parts.slice(1).join('.');
          
          // Handle line items separately (line_item_0.quantity -> line_items[0].quantity)
          if (firstPart.startsWith('line_item_')) {
            if (!userCorrected['line_items']) {
              userCorrected['line_items'] = [];
            }
            // Extract line ID from "line_item_0"
            const lineIdMatch = firstPart.match(/line_item_(\d+)/);
            if (lineIdMatch) {
              const lineIndex = parseInt(lineIdMatch[1]);
              // Ensure array is large enough
              while (userCorrected['line_items'].length <= lineIndex) {
                userCorrected['line_items'].push({});
              }
              userCorrected['line_items'][lineIndex][fieldName] = value;
            }
          } else {
            // Regular sections (meta, supplier, etc)
            if (!userCorrected[firstPart]) {
              userCorrected[firstPart] = {};
            }
            userCorrected[firstPart][fieldName] = value;
          }
        }
      });
      
      console.log("[Save] User corrected (structured):", userCorrected);
      
      // Send delta to backend for merge with existing data
      const body = {
        document_name: invoiceData.document_name,
        invoice_data_user_corrected: userCorrected,
        deleted_line_numbers: deletedLineNumbers
      };
      
      const response = await fetch(`${API_BASE_URL}/documents/${fullDocument.id}`, {
        method: "PUT",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to save document");
      }

      setSuccess(true);
      if (onSave) {
        onSave();
      }
      
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (err) {
      console.error("Error saving document:", err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // Determine if a field should be visible based on filters
  const showField = (
    isAdvanced,
    obligation,
    fieldValue,
    showNonMandatoryChecked,
    showAdvancedChecked,
    fieldProbability = null,
    mapid = null
  ) => {

    // Extract confidence thresholds from company settings
    const confidence_error_threshold = companySettings?.confidence_error_threshold || 0.8;
    const confidence_warning_threshold = companySettings?.confidence_warning_threshold || 0.85;
    const peppolIdRequired = companySettings?.peppol_id_required || false;
    const supplierRegistrationRequired = companySettings?.supplier_registration_required || false;

    // Determine if field is required (may be conditional based on settings)
    let required = obligation === "required";

    if (mapid == "supplier.peppol_id" || mapid == "customer.peppol_id") {
      console.log(mapid); 
      if (!peppolIdRequired) {
        required = false;
      }
    }
    if (mapid == "customer.legal_registration_number" ) {
      console.log(mapid); 
      if (!supplierRegistrationRequired) {  
        required = false;
      }
    }

    let probability = fieldProbability;
    if (probability === null || probability === undefined) {
      probability = 0.5; // Default to full confidence if not provided
    }

    let value = fieldValue;
    if (value === null || value === undefined) {
      value = '';
      probability = 1.0;
    }

    if(mapid==="payment.payment_means_code"){
      /*
      console.log(value);
      console.log(probability);
      console.log(required);
      console.log(showNonMandatoryChecked);
      console.log(showAdvancedChecked);  
      */ 
    }

    // Always show required fields
    if(required && value ==='') {
      return true;
    }

    // Always show required fields
    if(required && probability < confidence_error_threshold ) {
      return true;
    }

    // Hide non-required fields if "Show Optional" is unchecked
    if (!required && !showNonMandatoryChecked) {
      return false;
    }

    // Hide Advanced fields if "Show Advanced" is unchecked
    if (isAdvanced && !showAdvancedChecked) {
      return false;
    }
    return true;

  };

  return (
    <>
      <style>{`
        .info-icon {
          position: relative;
          cursor: help;
        }
        
        .tooltip-content {
          position: fixed;
          background: #1f2937;
          color: white;
          padding: 0.75rem;
          border-radius: 6px;
          font-size: 0.85rem;
          width: 220px;
          text-align: left;
          box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
          white-space: normal;
          z-index: 99999;
          pointer-events: auto;
          opacity: 0;
          visibility: hidden;
          transition: opacity 0.2s ease, visibility 0.2s ease;
        }
        
        .tooltip-content::before {
          content: '';
          position: absolute;
          bottom: -5px;
          left: 50%;
          transform: translateX(-50%);
          width: 0;
          height: 0;
          border-left: 5px solid transparent;
          border-right: 5px solid transparent;
          border-top: 5px solid #1f2937;
        }
        
        .info-icon:hover .tooltip-content {
          opacity: 1;
          visibility: visible;
        }
      `}</style>
    <div style={{
      position: "fixed",
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: "rgba(0, 0, 0, 0.5)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 1000,
    }}>
      <div style={{
        background: "white",
        borderRadius: isMaximized ? "0" : "8px",
        width: isMaximized ? "100%" : "90%",
        maxWidth: isMaximized ? "100%" : "1200px",
        height: isMaximized ? "100%" : "92vh",
        display: "flex",
        flexDirection: "column",
        boxShadow: isMaximized ? "none" : "0 20px 25px -5px rgba(0, 0, 0, 0.1)",
        position: "relative",
        boxSizing: "border-box",
      }}>
        {/* Header */}
        <div style={{
          padding: "1.5rem",
          borderBottom: "1px solid #e8ecf1",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "#f9fafb",
          flexShrink: 0,
        }}>
          <div>
            <h2 style={{ margin: 0, fontSize: "1.25rem", color: "#1a1a1a" }}>
              {invoiceData.document_name || document.raw_filename}
            </h2>
            <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.85rem", color: "#666" }}>
              Uploaded {new Date(document.created_at).toLocaleDateString("sv-SE")}
            </p>
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>

            <button
              onClick={() => setIsMaximized(!isMaximized)}
              style={{
                background: "none",
                border: "none",
                borderRadius: "4px",
                fontSize: "1rem",
                cursor: "pointer",
                color: "#666",
                padding: "0.5rem 0.75rem",
                transition: "all 0.2s ease",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              onMouseEnter={(e) => {
                e.target.style.opacity = "0.7";
              }}
              onMouseLeave={(e) => {
                e.target.style.opacity = "1";
              }}
              title={isMaximized ? "Exit fullscreen" : "Maximize"}
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                {isMaximized ? (
                  <>
                    <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
                  </>
                ) : (
                  <>
                    <path d="M14 3h7a1 1 0 0 1 1 1v7" />
                    <path d="M3 14v7a1 1 0 0 0 1 1h7" />
                    <path d="M6 9h12v8H6z" />
                    <path d="M9 14v4h6v-6" />
                  </>
                )}
              </svg>
            </button>
            <button
              onClick={onClose}
              style={{
                background: "none",
                border: "none",
                fontSize: "1.5rem",
                cursor: "pointer",
                color: "#666",
              }}
            >
              ×
            </button>
          </div>
        </div>

        {/* Content */}
        <div style={{
          display: "grid",
          gridTemplateColumns: isMaximized 
            ? `${showPreview ? "3fr" : "0px"} ${showForm ? "1fr" : "0px"}` 
            : `${showPreview ? "1fr" : "0px"} ${showForm ? "1fr" : "0px"}`,
          gap: "2rem",
          padding: "2rem",
          overflow: "hidden",
          flex: 1,
        }}>
          {/* Preview Panel */}
          <div style={{
            display: "flex",
            flexDirection: "column",
            overflow: "auto",
            transition: "all 0.3s ease",
            minWidth: 0,
          }}>
            <div style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1rem",
              position: "sticky",
              top: 0,
              background: "inherit",
              paddingBottom: "1rem",
              borderBottom: "1px solid #e8ecf1",
              zIndex: 10,
            }}>
              <h3 style={{ margin: 0, color: "#1a1a1a" }}>Document Preview</h3>
              <button
                onClick={togglePreview}
                style={{
                  padding: "0.4rem 0.5rem",
                  background: "none",
                  border: "1px solid #d0d0d0",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "1.2rem",
                  color: "#7265cf",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "32px",
                  height: "32px",
                  transition: "all 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.target.style.background = "#f5f5f5";
                  e.target.style.borderColor = "#999";
                }}
                onMouseLeave={(e) => {
                  e.target.style.background = "none";
                  e.target.style.borderColor = "#d0d0d0";
                }}
                title="Hide preview"
              >
                ◀
              </button>
            </div>
            <div style={{
              background: "#f5f7fa",
              borderRadius: "6px",
              padding: "1rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#999",
              overflow: "auto",
              flex: 1,
            }}>
              {document.raw_filename?.toLowerCase().endsWith('.pdf') ? (
                <iframe 
                  src={`${API_BASE_URL}/documents/${document.id}/preview`}
                  title="Document preview" 
                  style={{
                    width: "100%",
                    height: "100%",
                    border: "none",
                    borderRadius: "4px",
                  }}
                />
              ) : (
                <img 
                  src={`${API_BASE_URL}/documents/${document.id}/preview`}
                  alt="Document preview" 
                  style={{
                    maxWidth: "100%",
                    maxHeight: "100%",
                    objectFit: "contain",
                  }}
                />
              )}
            </div>
          </div>

          {/* Form */}
          <div style={{
            display: "flex",
            flexDirection: "column",
            overflow: "auto",
            minWidth: 0,
          }}>
            <div style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1rem",
              position: "sticky",
              top: 0,
              background: "white",
              paddingBottom: "1rem",
              borderBottom: "1px solid #e8ecf1",
              zIndex: 10,
            }}>
              <h3 style={{ margin: 0, color: "#1a1a1a" }}>Invoice Details</h3>
              <button
                onClick={toggleForm}
                style={{
                  padding: "0.4rem 0.5rem",
                  background: "none",
                  border: "1px solid #d0d0d0",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "1.2rem",
                  color: "#7265cf",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "32px",
                  height: "32px",
                  transition: "all 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.target.style.background = "#f5f5f5";
                  e.target.style.borderColor = "#999";
                }}
                onMouseLeave={(e) => {
                  e.target.style.background = "none";
                  e.target.style.borderColor = "#d0d0d0";
                }}
                title="Hide details"
              >
                ▶
              </button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem", height: "100%", minHeight: 0 }}>
              <div style={{ flexShrink: 0 }}>
                <label style={{ display: "block", fontWeight: "500", marginBottom: "0.5rem" }}>
                  Document Name
                </label>
                <input
                  type="text"
                  value={invoiceData.document_name}
                  onChange={(e) => handleFieldChange("document_name", e.target.value)}
                  onBlur={(e) => {
                    // If field is empty on blur, fill with raw_filename without extension
                    if (!e.target.value.trim()) {
                      const nameWithoutExt = fullDocument.raw_filename.split('.').slice(0, -1).join('.');
                      handleFieldChange("document_name", nameWithoutExt);
                    }
                  }}
                  style={{
                    width: "100%",
                    padding: "0.5rem",
                    border: "1px solid #ddd",
                    borderRadius: "4px",
                    fontSize: "0.9rem",
                    boxSizing: "border-box"
                  }}
                />
              </div>
              
              {/* PEPPOL Sections - Scrollable Container */}
              {Object.keys(peppol_sections).length > 0 && (
                <div style={{ 
                  marginTop: "0.5rem",
                  display: "flex",
                  flexDirection: "column",
                  minHeight: 0,
                  flex: 1
                }}>
                  <div style={{ marginBottom: "1rem", flexShrink: 0 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                      <p style={{ margin: 0, fontSize: "0.85rem", color: "#666", fontWeight: "500", display: "none" }}>
                        PEPPOL Sections ({
                          (() => {
                            const hasVisibleField = (fieldInfo, mapid = null) => {
                              return showField(
                                fieldInfo.Advanced === true,
                                fieldInfo.Obligation,
                                undefined, // fieldValue not needed for section visibility check
                                showNonMandatory,
                                showAdvanced,
                                fieldProbabilities[mapid] || null,
                                mapid
                              );
                            };

                            const hasVisibleNested = (nested) => {
                              if (!nested) return false;
                              for (let nestedName of Object.keys(nested)) {
                                const nestedData = nested[nestedName];
                                const nestedFields = nestedData.fields || nestedData;
                                for (let [btId, fieldInfo] of Object.entries(nestedFields)) {
                                  if (hasVisibleField(fieldInfo, btId)) {
                                    return true;
                                  }
                                }
                                if (hasVisibleNested(nestedData.nested)) return true;
                              }
                              return false;
                            };

                            return Object.entries(peppol_sections).filter(([sectionName, sectionData]) => {
                              const fields = sectionData.fields || sectionData;
                              const hasVisibleFields = Object.entries(fields).some(([mapid, f]) => hasVisibleField(f, mapid));
                              if (hasVisibleFields) return true;
                              if (hasVisibleNested(sectionData.nested)) return true;
                              return false;
                            }).length;
                          })()
                        })
                      </p>
                      <div style={{ display: "flex", gap: "1.5rem", justifyContent: "flex-end", alignItems: "center" }}>
                        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.85rem", cursor: "pointer" }}>
                          <input
                            type="checkbox"
                            checked={showNonMandatory}
                            onChange={(e) => setShowNonMandatory(e.target.checked)}
                            style={{ cursor: "pointer" }}
                          />
                          <span style={{ color: "#666" }}>Show Optional</span>
                        </label>
                        <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.85rem", cursor: "pointer" }}>
                          <input
                            type="checkbox"
                            checked={showAdvanced}
                            onChange={(e) => {
                              console.log('[TOGGLE] showAdvanced:', e.target.checked);
                              setShowAdvanced(e.target.checked);
                            }}
                            style={{ cursor: "pointer" }}
                          />
                          <span style={{ color: "#666" }}>Show Advanced</span>
                        </label>
                      </div>
                    </div>
                  </div>

                  <div style={{ 
                    overflowY: "auto",
                    paddingRight: "0.5rem",
                    flex: 1,
                    minHeight: 0
                  }}>
                    {/* Render all DisplayContext sections in contextOrder */}
                    {(() => {
                      const contextOrder = ['Invoice.Meta', 'Supplier', 'Customer', 'Payee', 'Tax Representative', 'Delivery', 'Payment', 'Charges.Discounts', 'Tax', 'Totals', 'LineItem'];
                      
                      // Filter sections that exist and have fields
                      const orderedSections = contextOrder.filter(context => peppol_sections[context]);
                      
                      return orderedSections.map(sectionName => {
                        const sectionData = peppol_sections[sectionName];
                        
                        // Special rendering for LineItem section
                        if (sectionName === 'LineItem') {
                          const lineItemFields = sectionData.fields || sectionData;
                          
                          return (
                            <div key={sectionName}>
                              <button
                                onClick={() => toggleSection(sectionName)}
                                style={{
                                  width: "100%",
                                  padding: "0.75rem 1rem",
                                  background: expandedSections[sectionName] ? "#f3f4f6" : "#ffffff",
                                  border: "1px solid #e5e7eb",
                                  borderRadius: "4px",
                                  cursor: "pointer",
                                  display: "flex",
                                  alignItems: "center",
                                  gap: "0.75rem",
                                  fontSize: "1rem",
                                  fontWeight: "600",
                                  color: "#1f2937",
                                  transition: "all 0.2s ease",
                                }}
                                onMouseEnter={(e) => { e.target.style.background = "#f9fafb"; e.target.style.borderColor = "#9ca3af"; }}
                                onMouseLeave={(e) => { e.target.style.background = expandedSections[sectionName] ? "#f3f4f6" : "#ffffff"; e.target.style.borderColor = "#e5e7eb"; }}
                              >
                                <span>{expandedSections[sectionName] ? "▼" : "▶"}</span>
                                <span>Document Lines ({lineItems.length})</span>
                                
                                {/* Summary metrics for all lines */}
                                <span style={{ marginLeft: "auto", fontSize: "0.8rem", color: "#9ca3af", display: "flex", alignItems: "center", gap: "0.75rem" }}>
                                  {(() => {
                                    // Calculate total metrics across all lines
                                    const peppolIdRequired = companySettings?.peppol_id_required || false;
                                    const supplierRegistrationRequired = companySettings?.supplier_registration_required || false;
                                    const allFields = Object.values(lineItemFields);
                                    // Exclude peppol_id and registration fields from mandatory count if not required
                                    const mandatoryFields = allFields.filter(f => {
                                      if (!peppolIdRequired && (f.mapid === "supplier.peppol_id" || f.mapid === "customer.peppol_id")) {
                                        return false; // Exclude peppol_id fields
                                      }
                                      if (!supplierRegistrationRequired && f.mapid === "customer.legal_registration_number") {
                                        return false; // Exclude registration field
                                      }
                                      return f.Obligation === "required";
                                    });
                                    const nonMandatoryFields = allFields.filter(f => f.Obligation !== "required");
                                    
                                    let totalFilledMandatory = 0;
                                    let totalMandatory = mandatoryFields.length * lineItems.length;
                                    
                                    lineItems.forEach(lineItem => {
                                      mandatoryFields.forEach(f => {
                                        const fieldMapid = `line_item_${lineItem.id}.${f.mapid.split('.').pop()}`;
                                        if (invoiceData[fieldMapid]) {
                                          totalFilledMandatory++;
                                        }
                                      });
                                    });
                                    
                                    const completionPercent = totalMandatory > 0 ? Math.round((totalFilledMandatory / totalMandatory) * 100) : 100;
                                    const barWidth = 60;
                                    
                                    return (
                                      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                                        {/* Progress bar */}
                                        <div style={{
                                          width: `${barWidth}px`,
                                          height: "6px",
                                          background: "#e5e7eb",
                                          borderRadius: "3px",
                                          overflow: "hidden",
                                          display: "flex"
                                        }}>
                                          {totalMandatory === 0 ? (
                                            <div style={{
                                              width: "100%",
                                              height: "100%",
                                              background: "#10b981",
                                              transition: "width 0.3s ease"
                                            }} />
                                          ) : completionPercent === 100 ? (
                                            <div style={{
                                              width: "100%",
                                              height: "100%",
                                              background: "#10b981",
                                              transition: "width 0.3s ease"
                                            }} />
                                          ) : totalFilledMandatory === 0 ? (
                                            <div style={{
                                              width: "100%",
                                              height: "100%",
                                              background: "#ef4444",
                                              transition: "width 0.3s ease"
                                            }} />
                                          ) : (
                                            <>
                                              <div style={{
                                                width: `${completionPercent}%`,
                                                height: "100%",
                                                background: "#9ca3af",
                                                transition: "width 0.3s ease"
                                              }} />
                                              <div style={{
                                                width: `${100 - completionPercent}%`,
                                                height: "100%",
                                                background: "#ef4444",
                                                transition: "width 0.3s ease"
                                              }} />
                                            </>
                                          )}
                                        </div>
                                        {/* Stats */}
                                        <span style={{ fontSize: "0.75rem", whiteSpace: "nowrap" }}>
                                          {totalFilledMandatory}/{totalMandatory}
                                        </span>
                                      </div>
                                    );
                                  })()}
                                </span>
                              </button>
                              
                              {expandedSections[sectionName] && (
                                <div style={{ 
                                  padding: "1rem", 
                                  background: "#f9fafb",
                                  borderRadius: "0 0 6px 6px",
                                  border: "1px solid #e5e7eb",
                                  borderTop: "none",
                                  marginBottom: "0.5rem"
                                }}>
                                  {/* Line Items Container */}
                                  <div style={{ display: "flex", flexDirection: "column", gap: "1rem", marginBottom: "1rem" }}>
                                    {lineItems.map((lineItem, index) => (
                                      <div key={lineItem.id} style={{
                                        border: "1px solid #d1d5db",
                                        borderRadius: "6px",
                                        background: "#ffffff",
                                        overflow: "hidden"
                                      }}>
                                        {/* Card Header */}
                                        <div
                                          onClick={() => toggleLineItem(lineItem.id)}
                                          style={{
                                            width: "100%",
                                            padding: "0.75rem 1rem",
                                            background: expandedLineItems[lineItem.id] ? "#f0f9ff" : "#ffffff",
                                            borderBottom: expandedLineItems[lineItem.id] ? "1px solid #bfdbfe" : "none",
                                            cursor: "pointer",
                                            display: "flex",
                                            alignItems: "center",
                                            gap: "0.75rem",
                                            justifyContent: "space-between",
                                            transition: "all 0.2s ease"
                                          }}
                                          onMouseEnter={(e) => { e.currentTarget.style.background = "#f0f9ff"; }}
                                          onMouseLeave={(e) => { e.currentTarget.style.background = expandedLineItems[lineItem.id] ? "#f0f9ff" : "#ffffff"; }}
                                        >
                                          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                                            <span style={{ fontSize: "0.9rem" }}>{expandedLineItems[lineItem.id] ? "▼" : "▶"}</span>
                                            <span style={{ fontWeight: "600", color: "#1f2937" }}>
                                              Line {index + 1}
                                            </span>
                                          </div>
                                          
                                          {/* Metrics for this line */}
                                          <div style={{ marginLeft: "auto", marginRight: "0.75rem", fontSize: "0.8rem", color: "#9ca3af", display: "flex", alignItems: "center", gap: "0.75rem" }}>
                                            {(() => {
                                              const peppolIdRequired = companySettings?.peppol_id_required || false;
                                              const supplierRegistrationRequired = companySettings?.supplier_registration_required || false;
                                              const allFields = Object.values(lineItemFields);
                                              // Exclude peppol_id and registration fields from mandatory count if not required
                                              const mandatoryFields = allFields.filter(f => {
                                                if (!peppolIdRequired && (f.mapid === "supplier.peppol_id" || f.mapid === "customer.peppol_id")) {
                                                  return false; // Exclude peppol_id fields
                                                }
                                                if (!supplierRegistrationRequired && f.mapid === "customer.legal_registration_number") {
                                                  return false; // Exclude registration field
                                                }
                                                return f.Obligation === "required";
                                              });
                                              const filledMandatory = mandatoryFields.filter(f => {
                                                const fieldMapid = `line_item_${lineItem.id}.${f.mapid.split('.').pop()}`;
                                                return !!invoiceData[fieldMapid];
                                              }).length;
                                              const totalMandatory = mandatoryFields.length;
                                              const nonMandatoryFields = allFields.filter(f => f.Obligation !== "required");
                                              
                                              const completionPercent = totalMandatory > 0 ? Math.round((filledMandatory / totalMandatory) * 100) : 100;
                                              const barWidth = 50;
                                              
                                              return (
                                                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                                                  {/* Progress bar */}
                                                  <div style={{
                                                    width: `${barWidth}px`,
                                                    height: "6px",
                                                    background: "#e5e7eb",
                                                    borderRadius: "3px",
                                                    overflow: "hidden",
                                                    display: "flex"
                                                  }}>
                                                    {totalMandatory === 0 ? (
                                                      <div style={{
                                                        width: "100%",
                                                        height: "100%",
                                                        background: "#10b981",
                                                        transition: "width 0.3s ease"
                                                      }} />
                                                    ) : completionPercent === 100 ? (
                                                      <div style={{
                                                        width: "100%",
                                                        height: "100%",
                                                        background: "#10b981",
                                                        transition: "width 0.3s ease"
                                                      }} />
                                                    ) : filledMandatory === 0 ? (
                                                      <div style={{
                                                        width: "100%",
                                                        height: "100%",
                                                        background: "#ef4444",
                                                        transition: "width 0.3s ease"
                                                      }} />
                                                    ) : (
                                                      <>
                                                        <div style={{
                                                          width: `${completionPercent}%`,
                                                          height: "100%",
                                                          background: "#9ca3af",
                                                          transition: "width 0.3s ease"
                                                        }} />
                                                        <div style={{
                                                          width: `${100 - completionPercent}%`,
                                                          height: "100%",
                                                          background: "#ef4444",
                                                          transition: "width 0.3s ease"
                                                        }} />
                                                      </>
                                                    )}
                                                  </div>
                                                  {/* Stats */}
                                                  <span style={{ fontSize: "0.75rem", whiteSpace: "nowrap" }}>
                                                    {filledMandatory}/{totalMandatory}
                                                  </span>
                                                </div>
                                              );
                                            })()}
                                          </div>
                                          
                                          <div style={{ display: "flex", gap: "0.5rem" }}>
                                            {lineItems.length > 1 && (
                                              <button
                                                onClick={(e) => {
                                                  e.stopPropagation();
                                                  removeLineItem(lineItem.id);
                                                }}
                                                style={{
                                                  padding: "0.4rem 0.6rem",
                                                  background: "#fee2e2",
                                                  border: "1px solid #fca5a5",
                                                  color: "#991b1b",
                                                  borderRadius: "3px",
                                                  cursor: "pointer",
                                                  fontSize: "0.85rem",
                                                  fontWeight: "500",
                                                  transition: "all 0.2s ease"
                                                }}
                                                onMouseEnter={(e) => { e.target.style.background = "#fecaca"; }}
                                                onMouseLeave={(e) => { e.target.style.background = "#fee2e2"; }}
                                              >
                                                Remove
                                              </button>
                                            )}
                                          </div>
                                        </div>
                                        
                                        {/* Card Content */}
                                        {expandedLineItems[lineItem.id] && (
                                          <div style={{ 
                                            padding: "1rem",
                                            display: "grid",
                                            gridTemplateColumns: "1fr 1fr",
                                            gap: "1rem"
                                          }}>
                                            {Object.entries(lineItemFields).map(([mapid, fieldInfo]) => {
                                              const lineItemMapid = `line_item_${lineItem.id}.${mapid.split('.').pop()}`;
                                              const isRequired = fieldInfo.Obligation === "required";
                                              const hasValue = !!invoiceData[lineItemMapid];
                                              const isEmpty = !hasValue;
                                              // Check if this is line_number field (could be 'line_number' or end with '.line_number')
                                              const isLineNumberField = mapid === 'line_number' || mapid.endsWith('.line_number');
                                              
                                              return (
                                                <div key={lineItemMapid} style={{ display: "flex", flexDirection: "column" }}>
                                                  <label style={{
                                                    display: "flex",
                                                    alignItems: "center",
                                                    gap: "0.5rem",
                                                    fontWeight: "500",
                                                    marginBottom: "0.5rem",
                                                    color: "#374151",
                                                    fontSize: "0.9rem"
                                                  }}>
                                                    <span style={{
                                                      fontWeight: "600",
                                                      color: isRequired ? "#1f2937" : "#9ca3af"
                                                    }}>
                                                      {fieldInfo["DisplayName"] || mapid}
                                                    </span>
                                                    {isRequired && !hasValue && <span style={{ color: "#dc2626" }}>*</span>}
                                                  </label>
                                                  <input
                                                    type={fieldInfo.Type === "number" ? "number" : "text"}
                                                    value={invoiceData[lineItemMapid] || ""}
                                                    onChange={(e) => {
                                                      setInvoiceData(prev => ({
                                                        ...prev,
                                                        [lineItemMapid]: e.target.value
                                                      }));
                                                    }}
                                                    readOnly={isLineNumberField}
                                                    placeholder={fieldInfo.Example || ""}
                                                    style={{
                                                      padding: "0.5rem 0.75rem",
                                                      border: isRequired && isEmpty ? "2px solid #dc2626" : "1px solid #d0d0d0",
                                                      borderRadius: "4px",
                                                      fontSize: "0.9rem",
                                                      fontFamily: "inherit",
                                                      outline: "none",
                                                      transition: "border-color 0.2s ease",
                                                      background: isLineNumberField ? "#f3f4f6" : "white",
                                                      cursor: isLineNumberField ? "not-allowed" : "text"
                                                    }}
                                                    onFocus={(e) => { if (!isLineNumberField) e.target.style.borderColor = "#3b82f6"; }}
                                                    onBlur={(e) => { e.target.style.borderColor = isRequired && isEmpty ? "#dc2626" : "#d0d0d0"; }}
                                                  />
                                                </div>
                                              );
                                            })}
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                  
                                  {/* Add Button */}
                                  <button
                                    onClick={addLineItem}
                                    style={{
                                      width: "100%",
                                      padding: "0.75rem 1rem",
                                      background: "#dbeafe",
                                      border: "1px dashed #3b82f6",
                                      color: "#1e40af",
                                      borderRadius: "4px",
                                      cursor: "pointer",
                                      fontSize: "0.9rem",
                                      fontWeight: "500",
                                      transition: "all 0.2s ease"
                                    }}
                                    onMouseEnter={(e) => { e.target.style.background = "#bfdbfe"; }}
                                    onMouseLeave={(e) => { e.target.style.background = "#dbeafe"; }}
                                  >
                                    + Add Document Line
                                  </button>
                                </div>
                              )}
                            </div>
                          );
                        }
                        
                        // Regular section rendering for non-LineItem sections
                        const fieldsInSection = sectionData.fields || sectionData;
                        
                        // Filter fields based on checkboxes
                        const filteredFields = Object.entries(fieldsInSection)
                          .filter(([mapid, fieldInfo]) => {
                            return showField(
                              fieldInfo.Advanced === true,
                              fieldInfo.Obligation,
                              invoiceData[mapid],
                              showNonMandatory,
                              showAdvanced,
                              fieldProbabilities[mapid] || null,
                              mapid
                            );
                          })
                          .reduce((acc, [mapid, fieldInfo]) => {
                            acc[mapid] = fieldInfo;
                            return acc;
                          }, {});
                        
                        // Hide section if no fields after filtering
                        if (Object.keys(filteredFields).length === 0) return null;
                        
                        return (
                          <div key={sectionName}>
                            <button
                              onClick={() => toggleSection(sectionName)}
                              style={{
                                width: "100%",
                                padding: "0.75rem 1rem",
                                background: expandedSections[sectionName] ? "#f3f4f6" : "#ffffff",
                                border: "1px solid #e5e7eb",
                                borderRadius: "4px",
                                cursor: "pointer",
                                display: "flex",
                                alignItems: "center",
                                gap: "0.75rem",
                                fontSize: "0.9rem",
                                fontWeight: "500",
                                color: "#1f2937",
                                marginBottom: "0.5rem",
                                transition: "all 0.2s ease",
                              }}
                              onMouseEnter={(e) => {
                                e.target.style.background = expandedSections[sectionName] ? "#f3f4f6" : "#f9fafb";
                                e.target.style.borderColor = "#9ca3af";
                              }}
                              onMouseLeave={(e) => {
                                e.target.style.background = expandedSections[sectionName] ? "#f3f4f6" : "#ffffff";
                                e.target.style.borderColor = "#e5e7eb";
                              }}
                            >
                              <span style={{ display: "inline-block", transform: expandedSections[sectionName] ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.2s", width: "14px" }}>
                                ▶
                              </span>
                              <span>{sectionName}</span>
                              <span style={{ marginLeft: "auto", fontSize: "0.8rem", color: "#9ca3af", display: "flex", alignItems: "center", gap: "0.75rem" }}>
                                {(() => {
                                  // Calculate metrics for this section
                                  const peppolIdRequired = companySettings?.peppol_id_required || false;
                                  const supplierRegistrationRequired = companySettings?.supplier_registration_required || false;
                                  const allFields = Object.values(fieldsInSection);
                                  // Exclude peppol_id and registration fields from mandatory count if not required
                                  const mandatoryFields = allFields.filter(f => {
                                    if (!peppolIdRequired && (f.mapid === "supplier.peppol_id" || f.mapid === "customer.peppol_id")) {
                                      return false; // Exclude peppol_id fields
                                    }
                                    if (!supplierRegistrationRequired && f.mapid === "customer.legal_registration_number") {
                                      return false; // Exclude registration field
                                    }
                                    return f.Obligation === "required";
                                  });
                                  const filledMandatory = mandatoryFields.filter(f => invoiceData[f.mapid]).length;
                                  const totalMandatory = mandatoryFields.length;
                                  const nonMandatoryFields = allFields.filter(f => f.Obligation !== "required");
                                  
                                  const completionPercent = totalMandatory > 0 ? Math.round((filledMandatory / totalMandatory) * 100) : 100;
                                  const barWidth = 60;
                                  
                                  return (
                                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                                      {/* Progress bar */}
                                      <div style={{
                                        width: `${barWidth}px`,
                                        height: "6px",
                                        background: "#e5e7eb",
                                        borderRadius: "3px",
                                        overflow: "hidden",
                                        display: "flex"
                                      }}>
                                        {totalMandatory === 0 ? (
                                          <div style={{
                                            width: "100%",
                                            height: "100%",
                                            background: "#10b981",
                                            transition: "width 0.3s ease"
                                          }} />
                                        ) : completionPercent === 100 ? (
                                          <div style={{
                                            width: "100%",
                                            height: "100%",
                                            background: "#10b981",
                                            transition: "width 0.3s ease"
                                          }} />
                                        ) : filledMandatory === 0 ? (
                                          <div style={{
                                            width: "100%",
                                            height: "100%",
                                            background: "#ef4444",
                                            transition: "width 0.3s ease"
                                          }} />
                                        ) : (
                                          <>
                                            <div style={{
                                              width: `${completionPercent}%`,
                                              height: "100%",
                                              background: "#9ca3af",
                                              transition: "width 0.3s ease"
                                            }} />
                                            <div style={{
                                              width: `${100 - completionPercent}%`,
                                              height: "100%",
                                              background: "#ef4444",
                                              transition: "width 0.3s ease"
                                            }} />
                                          </>
                                        )}
                                      </div>
                                      {/* Stats */}
                                      <span style={{ fontSize: "0.75rem", whiteSpace: "nowrap" }}>
                                        {filledMandatory}/{totalMandatory} | {nonMandatoryFields.length}
                                      </span>
                                    </div>
                                  );
                                })()}
                              </span>
                            </button>
                            
                            {expandedSections[sectionName] && (
                              <div style={{ 
                                padding: "1rem", 
                                background: "#f9fafb",
                                borderRadius: "0 0 6px 6px",
                                border: "1px solid #e5e7eb",
                                borderTop: "none",
                                marginBottom: "0.5rem"
                              }}>
                                <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "1rem" }}>
                                  {Object.entries(filteredFields).map(([mapid, fieldInfo]) => (
                                    <div key={mapid} style={{ display: "flex", flexDirection: "column" }}>
                                      <label 
                                        style={{ 
                                          display: "flex",
                                          alignItems: "center",
                                          gap: "0.5rem",
                                          fontWeight: "500", 
                                          marginBottom: "0.5rem",
                                          color: "#374151",
                                          cursor: "help",
                                        }}
                                      >
                                        <span style={{ fontWeight: "600", color: fieldInfo.Obligation === "required" ? "#1f2937" : "#9ca3af", fontSize: "0.95rem" }}>
                                          {fieldInfo["DisplayName"] || fieldInfo["TagName"]}
                                        </span>
                                        <div
                                          className="info-icon"
                                          style={{
                                            display: "inline-flex",
                                            alignItems: "center",
                                            justifyContent: "center",
                                            width: "18px",
                                            height: "18px",
                                            borderRadius: "50%",
                                            border: "1px solid #9ca3af",
                                            fontSize: "0.75rem",
                                            color: "#9ca3af",
                                            fontWeight: "600",
                                            cursor: "pointer",
                                          }}
                                          onMouseEnter={(e) => {
                                            const rect = e.currentTarget.getBoundingClientRect();
                                            const tooltip = e.currentTarget.querySelector('.tooltip-content');
                                            if (tooltip) {
                                              tooltip.style.top = (rect.top - tooltip.offsetHeight - 10) + "px";
                                              tooltip.style.left = (rect.left + rect.width / 2 - 110) + "px";
                                            }
                                          }}
                                        >
                                          i
                                          <div className="tooltip-content">
                                            <div style={{
                                              color: "#60a5fa",
                                              fontWeight: "600",
                                              marginBottom: "0.5rem",
                                            }}>
                                              {fieldInfo["BT-ID"] && fieldInfo["BT-ID"] !== 'N/A' && (
                                                <a href={`https://docs.peppol.eu/poacc/billing/3.0/#${fieldInfo["BT-ID"]}`} target="_blank" rel="noopener noreferrer" style={{ color: "#60a5fa", textDecoration: "underline" }}>{fieldInfo["BT-ID"]}</a>
                                              )}
                                            </div>
                                            {fieldInfo["Advanced"] && (
                                              <div style={{ fontSize: "0.75rem", color: "#f59e0b", marginBottom: "0.4rem", fontWeight: "600" }}>
                                                ⚠️ Advanced Field
                                              </div>
                                            )}
                                            <div style={{ fontSize: "0.75rem", color: "#d1d5db", marginBottom: "0.4rem" }}>
                                              {fieldInfo["Obligation"] === "required" ? "🔴 Required" : fieldInfo["Obligation"] === "conditional" ? "🟡 Conditional" : "🟢 Optional"}
                                            </div>
                                            {fieldInfo["ConditionalDescription"] && (
                                              <div style={{ fontSize: "0.75rem", color: "#e5e7eb", marginBottom: "0.4rem", fontStyle: "italic" }}>
                                                <strong>Condition:</strong> {fieldInfo["ConditionalDescription"]}
                                              </div>
                                            )}
                                            <div style={{ fontSize: "0.8rem", color: "#e5e7eb", marginTop: "0.5rem" }}>
                                              {fieldInfo["Description"]}
                                            </div>
                                          </div>
                                        </div>
                                        <span style={{ borderBottom: "1px dotted #9ca3af", fontSize: "0.75rem", color: "#6b7280", display: "none" }}>
                                          {fieldInfo["TagName"]}
                                        </span>
                                      </label>
                                      <input
                                        type="text"
                                        value={invoiceData[mapid] || ""}
                                        onChange={(e) => handleFieldChange(mapid, e.target.value)}
                                        placeholder={fieldInfo["Example"] ? `Ex: ${fieldInfo["Example"]}` : `Enter ${mapid}`}
                                        title={fieldInfo["Description"]}
                                        style={{
                                          width: "100%",
                                          padding: "0.75rem",
                                          border: (fieldInfo.Obligation === "required" && !invoiceData[mapid]) ? "2px solid #dc2626" : fieldInfo.Advanced ? "2px dotted #9ca3af" : "1px solid #d0d0d0",
                                          borderRadius: "6px",
                                          fontSize: "0.95rem",
                                          boxSizing: "border-box",
                                        }}
                                      />
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      });
                    })()}
                    </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Collapsed Preview Tab */}
        {!showPreview && (
        <div style={{
          position: "absolute",
          left: 0,
          top: "110px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "white",
          border: "1px solid #d0d0d0",
          borderRadius: "0 6px 6px 0",
          cursor: "pointer",
          transition: "all 0.2s ease",
          paddingBottom: "1rem",
          paddingTop: "1rem",
          paddingLeft: "0.5rem",
          paddingRight: "0.5rem",
          height: "auto",
          zIndex: 20,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "#f5f5f5";
          e.currentTarget.style.borderColor = "#999";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "white";
          e.currentTarget.style.borderColor = "#d0d0d0";
        }}
        onClick={togglePreview}
        title="Show preview"
        >
          <div style={{
            writingMode: "vertical-lr",
            textOrientation: "mixed",
            color: "#7265cf",
            fontSize: "0.8rem",
            fontWeight: "700",
            marginBottom: "0.8rem",
            letterSpacing: "0.5px",
          }}>
            PREVIEW
          </div>
          <div style={{
            fontSize: "1.8rem",
            color: "#7265cf",
            fontWeight: "bold",
            transition: "transform 0.2s ease",
          }}>
            ▶
          </div>
        </div>
        )}

        {/* Collapsed Form Tab */}
        {!showForm && (
        <div style={{
          position: "absolute",
          right: 0,
          top: "110px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "white",
          border: "1px solid #d0d0d0",
          borderRadius: "6px 0 0 6px",
          cursor: "pointer",
          transition: "all 0.2s ease",
          paddingBottom: "1rem",
          paddingTop: "1rem",
          paddingLeft: "0.5rem",
          paddingRight: "0.5rem",
          height: "auto",
          zIndex: 20,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "#f5f5f5";
          e.currentTarget.style.borderColor = "#999";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "white";
          e.currentTarget.style.borderColor = "#d0d0d0";
        }}
        onClick={toggleForm}
        title="Show form"
        >
          <div style={{
            writingMode: "vertical-rl",
            textOrientation: "mixed",
            color: "#7265cf",
            fontSize: "0.8rem",
            fontWeight: "700",
            marginBottom: "0.8rem",
            letterSpacing: "0.5px",
          }}>
            DETAILS
          </div>
          <div style={{
            fontSize: "1.8rem",
            color: "#7265cf",
            fontWeight: "bold",
            transition: "transform 0.2s ease",
          }}>
            ◀
          </div>
        </div>
        )}

        {/* Error/Success Messages */}
        {error && (
          <div style={{
            margin: "0 2rem",
            padding: "1rem",
            background: "#fee",
            borderRadius: "6px",
            borderLeft: "4px solid #ef4444",
            color: "#991b1b",
          }}>
            Error: {error}
          </div>
        )}

        {success && (
          <div style={{
            margin: "0 2rem",
            padding: "1rem",
            background: "#f0fdf4",
            borderRadius: "6px",
            borderLeft: "4px solid #10b981",
            color: "#166534",
          }}>
            ✓ Document saved successfully!
          </div>
        )}

        {/* Footer Actions */}
        <div style={{
          padding: "1.5rem 2rem",
          borderTop: "1px solid #e8ecf1",
          display: "flex",
          gap: "1rem",
          justifyContent: "space-between",
          background: "#f9fafb",
          flexShrink: 0,
        }}>
          {isAdmin && (
            <button
              onClick={() => setShowAdvancedAnalysis(true)}
              style={{
                padding: "0.75rem 1.5rem",
                background: "#e5e7eb",
                color: "#1a1a1a",
                border: "1px solid #d0d0d0",
                borderRadius: "6px",
                cursor: "pointer",
                fontWeight: "600",
              }}
            >
              Advanced Analysis
            </button>
          )}
          <div style={{ display: "flex", gap: "1rem" }}>
            <button
              onClick={onClose}
              disabled={isLoading}
              style={{
                padding: "0.75rem 1.5rem",
                background: "white",
                color: "#1a1a1a",
                border: "1px solid #d0d0d0",
                borderRadius: "6px",
                cursor: "pointer",
                fontWeight: "600",
                opacity: isLoading ? 0.6 : 1,
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={isLoading}
              style={{
                padding: "0.75rem 1.5rem",
                background: "#7265cf",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: isLoading ? "not-allowed" : "pointer",
                fontWeight: "600",
                opacity: isLoading ? 0.7 : 1,
              }}
            >
              {isLoading ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </div>
      </div>
    </div>
    
    {/* Advanced Analysis Modal */}
    {showAdvancedAnalysis && (
      <div style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0, 0, 0, 0.7)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 2000,
      }}>
        <div style={{
          background: "white",
          borderRadius: "12px",
          width: "95%",
          maxWidth: "1400px",
          maxHeight: "95vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
          position: "relative",
          overflow: "hidden",
        }}>
          {/* Modal Header */}
          <div style={{
            padding: "1.5rem 2rem",
            borderBottom: "1px solid #e5e7eb",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            background: "#f9fafb",
          }}>
            <h2 style={{ margin: 0, fontSize: "1.5rem", color: "#1a1a1a" }}>
              Advanced Invoice Analysis
            </h2>
            <button
              onClick={() => setShowAdvancedAnalysis(false)}
              style={{
                background: "none",
                border: "none",
                fontSize: "2rem",
                cursor: "pointer",
                color: "#666",
                width: "40px",
                height: "40px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              ×
            </button>
          </div>

          {/* Modal Content */}
          <div style={{
            flex: 1,
            overflow: "auto",
            padding: "2rem",
            background: "#fafbfc",
          }}>
            {/* Statistics Dashboard - Above Tabs */}
            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: "1rem",
              marginBottom: "2rem",
            }}>
              <div style={{
                background: "white",
                borderRadius: "8px",
                padding: "1.5rem",
                border: "1px solid #e5e7eb",
                textAlign: "center",
              }}>
                <div style={{ fontSize: "0.875rem", color: "#6b7280", marginBottom: "0.75rem", fontWeight: "500" }}>
                  Processing Status
                </div>
                <div style={{ fontSize: "1.25rem", fontWeight: "600", color: "#1a1a1a" }}>
                  {fullDocument.status || "N/A"}
                </div>
              </div>
              <div style={{
                background: "white",
                borderRadius: "8px",
                padding: "1.5rem",
                border: "1px solid #e5e7eb",
                textAlign: "center",
              }}>
                <div style={{ fontSize: "0.875rem", color: "#6b7280", marginBottom: "0.75rem", fontWeight: "500" }}>
                  Predicted Accuracy
                </div>
                <div style={{ fontSize: "1.875rem", fontWeight: "bold", color: "#7265cf" }}>
                  {(parseFloat(fullDocument.predicted_accuracy) || 0).toFixed(1)}%
                </div>
              </div>
              <div style={{
                background: "white",
                borderRadius: "8px",
                padding: "1.5rem",
                border: "1px solid #e5e7eb",
                textAlign: "center",
              }}>
                <div style={{ fontSize: "0.875rem", color: "#6b7280", marginBottom: "0.75rem", fontWeight: "500" }}>
                  Training Data
                </div>
                <div style={{ fontSize: "1.25rem", fontWeight: "600", color: fullDocument.is_training ? "#10b981" : "#6b7280" }}>
                  {fullDocument.is_training ? "Yes" : "No"}
                </div>
              </div>
            </div>

            {/* Tabs */}
            <div style={{
              display: "flex",
              gap: "1rem",
              marginBottom: "2rem",
              borderBottom: "1px solid #e5e7eb",
            }}>
              <button
                onClick={() => setActiveAnalysisTab("extraction")}
                style={{
                  padding: "0.75rem 1.5rem",
                  border: "none",
                  background: "transparent",
                  cursor: "pointer",
                  fontSize: "1rem",
                  fontWeight: "600",
                  color: activeAnalysisTab === "extraction" ? "#1f2937" : "#6b7280",
                  borderBottom: activeAnalysisTab === "extraction" ? "3px solid #7265cf" : "3px solid transparent",
                  paddingBottom: "calc(0.75rem - 3px)",
                }}
              >
                Data Extraction
              </button>

            </div>

            {/* Tab Content: Data Extraction */}
            {activeAnalysisTab === "extraction" && (
            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr",
              gap: "2rem",
            }}>
              {/* Content Type */}
              <div style={{
                background: "white",
                borderRadius: "8px",
                padding: "1.5rem",
                border: "1px solid #e5e7eb",
                maxWidth: "100%",
                overflow: "hidden",
              }}>
                <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.125rem", color: "#1a1a1a" }}>
                  Content Type
                </h3>
                <pre style={{
                  background: "#1a1a1a",
                  color: "#00ff00",
                  padding: "1rem",
                  borderRadius: "6px",
                  fontSize: "0.85rem",
                  overflow: "auto",
                  maxHeight: "300px",
                  fontFamily: "monospace",
                  lineHeight: "1.6",
                }}>
                  {(() => {
                    try {
                      const data = typeof fullDocument.content_type === 'string' 
                        ? JSON.parse(fullDocument.content_type) 
                        : fullDocument.content_type || {};
                      return formatJsonCompact(data);
                    } catch (e) {
                      return formatJsonCompact(fullDocument.content_type || {});
                    }
                  })()}
                </pre>
              </div>

              {/* LLM Predicted Invoice Data */}
              <div style={{
                background: "white",
                borderRadius: "8px",
                padding: "1.5rem",
                border: "1px solid #e5e7eb",
                maxWidth: "100%",
                overflow: "hidden",
              }}>
                <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.125rem", color: "#1a1a1a" }}>
                  LLM Predicted Invoice Data
                </h3>
                <pre style={{
                  background: "#1a1a1a",
                  color: "#00ff00",
                  padding: "1rem",
                  borderRadius: "6px",
                  fontSize: "0.85rem",
                  overflow: "auto",
                  maxHeight: "300px",
                  fontFamily: "monospace",
                  lineHeight: "1.6",
                }}>
                  {(() => {
                    try {
                      const data = typeof fullDocument.invoice_data_raw === 'string' 
                        ? JSON.parse(fullDocument.invoice_data_raw) 
                        : fullDocument.invoice_data_raw || {};
                      return formatJsonCompact(data);
                    } catch (e) {
                      return fullDocument.invoice_data_raw || "N/A";
                    }
                  })()}
                </pre>
              </div>

              {/* PEPPOL Predicted Data */}
              <div style={{
                background: "white",
                borderRadius: "8px",
                padding: "1.5rem",
                border: "1px solid #e5e7eb",
                maxWidth: "100%",
                overflow: "hidden",
              }}>
                <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.125rem", color: "#1a1a1a" }}>
                  PEPPOL Predicted
                </h3>
                <pre style={{
                  background: "#1a1a1a",
                  color: "#00ff00",
                  padding: "1rem",
                  borderRadius: "6px",
                  fontSize: "0.85rem",
                  overflow: "auto",
                  maxHeight: "300px",
                  fontFamily: "monospace",
                  lineHeight: "1.6",
                }}>
                  {(() => {
                    try {
                      const data = typeof fullDocument.invoice_data_peppol === 'string' 
                        ? JSON.parse(fullDocument.invoice_data_peppol) 
                        : fullDocument.invoice_data_peppol || {};
                      return formatJsonCompact(data);
                    } catch (e) {
                      return fullDocument.invoice_data_peppol || "N/A";
                    }
                  })()}
                </pre>
              </div>

              {/* User Corrected Invoice Data */}
              <div style={{
                background: "white",
                borderRadius: "8px",
                padding: "1.5rem",
                border: "1px solid #e5e7eb",
                maxWidth: "100%",
                overflow: "hidden",
              }}>
                <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.125rem", color: "#1a1a1a" }}>
                  User Corrected
                </h3>
                <pre style={{
                  background: "#1a1a1a",
                  color: "#00ff00",
                  padding: "1rem",
                  borderRadius: "6px",
                  fontSize: "0.85rem",
                  overflow: "auto",
                  maxHeight: "300px",
                  fontFamily: "monospace",
                  lineHeight: "1.6",
                }}>
                  {(() => {
                    try {
                      const data = typeof fullDocument.invoice_data_user_corrected === 'string' 
                        ? JSON.parse(fullDocument.invoice_data_user_corrected) 
                        : fullDocument.invoice_data_user_corrected || {};
                      return formatJsonCompact(data);
                    } catch (e) {
                      return fullDocument.invoice_data_user_corrected || "N/A";
                    }
                  })()}
                </pre>
              </div>

              {/* Final PEPPOL Data */}
              <div style={{
                background: "white",
                borderRadius: "8px",
                padding: "1.5rem",
                border: "1px solid #e5e7eb",
                maxWidth: "100%",
                overflow: "hidden",
              }}>
                <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.125rem", color: "#1a1a1a" }}>
                  Final PEPPOL Data
                </h3>
                <pre style={{
                  background: "#1a1a1a",
                  color: "#00ff00",
                  padding: "1rem",
                  borderRadius: "6px",
                  fontSize: "0.85rem",
                  overflow: "auto",
                  maxHeight: "300px",
                  fontFamily: "monospace",
                  lineHeight: "1.6",
                }}>
                  {(() => {
                    try {
                      const data = typeof fullDocument.invoice_data_peppol_final === 'string' 
                        ? JSON.parse(fullDocument.invoice_data_peppol_final) 
                        : fullDocument.invoice_data_peppol_final || {};
                      return formatJsonCompact(data);
                    } catch (e) {
                      return fullDocument.invoice_data_peppol_final || "N/A";
                    }
                  })()}
                </pre>
              </div>
            </div>
            )}
            </div>

          {/* Modal Footer */}
          <div style={{
            padding: "1.5rem 2rem",
            borderTop: "1px solid #e5e7eb",
            display: "flex",
            gap: "1rem",
            justifyContent: "flex-end",
            background: "#f9fafb",
          }}>
            <button
              onClick={() => setShowAdvancedAnalysis(false)}
              style={{
                padding: "0.75rem 2rem",
                background: "#7265cf",
                color: "white",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
                fontWeight: "600",
                fontSize: "1rem",
              }}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    )}
    </>
  );
}

export default DocumentDetail;
